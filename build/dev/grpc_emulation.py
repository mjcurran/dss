import os
import time
import logging
import argparse

from core.api.grpc.client import CoreGrpcClient, InterfaceHelper
from core.api.grpc.wrappers import NodeType, Position, SessionLocation, Geo, ConfigOption, ConfigOptionType
from core.emane.models.ieee80211abg import EmaneIeee80211abgModel
from core.location.geo import GeoLocation
from core import utils

def node_command(node, cmd):
    dcmd = f"docker exec {node.name} {cmd}"
    utils.cmd(dcmd, wait=False, shell=False)


def main():

    mariadb_image =  "uss-sp-mariadb"
    mongodb_image =  "pierce-mongo"
    sp_image =  "uss-sp-api"
    nginx_image =  "pierce-nginx"
    drone_image =  "python-drone"
    cockroach_image = "cockroachdb/cockroach:latest"
    dss_service_image = "interuss-test"
    auth_image = "core-oauth"

    # Setup Session
    client = CoreGrpcClient()
    #with client.context_connect():
    #    session = client.create_session()
    client.connect()
    session = client.create_session()

    session.set_options({"controlnet": "172.16.0.0/24"})
    #location: SessionLocation = SessionLocation(
    #    x=0.0, y=0.0, z=0.0, lat=47.57917, lon=-122.13232, alt=2.0, scale=150.0
    #)
    # 41.698361, -86.233894
    center = SessionLocation(x=0.0, y=0.0, z=0.0, lat=41.702, lon=-86.235564, alt=2.0, scale=150.0)
    session.location = center

    # Helpers
    def infinite_sequence():
        num = 1
        while True:
            yield num
            num += 1

    nodeIds = infinite_sequence()

    # Internet Nodes
    pInternet = InterfaceHelper(ip4_prefix="10.83.0.0/24")
    sInternet = session.add_node(
        next(nodeIds), _type=NodeType.SWITCH, position=Position(x=150, y=150)
    )
    sInternet.icon = "wlan_icon45.png"

    #service provider host
    nUSS = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="USS",
        model=None,
        image=sp_image,
        position=Position(x=400, y=100),
    )
    nUSS.icon = "host.gif"
    session.add_link(node1=nUSS, node2=sInternet, iface1=pInternet.create_iface(nUSS.id, 0))

    #service provider DB
    spDB = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="MariaDB",
        model=None,
        image=mariadb_image,
        position=Position(x=400, y=80),
    )
    spDB.icon = "database_icon.png"
    session.add_link(node1=spDB, node2=sInternet, iface1=pInternet.create_iface(spDB.id, 0))

    #cockroachDB
    cockroach = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="cockroachDB",
        model=None,
        image=cockroach_image,
        position=Position(x=20, y=420),
    )
    cockroach.icon = "database_icon.png"
    session.add_link(node1=cockroach, node2=sInternet, iface1=pInternet.create_iface(cockroach.id, 0))

    #auth service
    oauth = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="OAuth",
        model=None,
        image=auth_image,
        position=Position(x=50, y=40),
    )
    oauth.icon = "oauth_icon.png"
    session.add_link(node1=oauth, node2=sInternet, iface1=pInternet.create_iface(oauth.id, 0))

    # DSS core service
    nDSS = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="DSS",
        model=None,
        image=dss_service_image,
        position=Position(x=100, y=400),
    )
    nDSS.icon = "host.gif"
    session.add_link(node1=nDSS, node2=sInternet, iface1=pInternet.create_iface(nDSS.id, 0))

    #DSS gateway
    dssGateway = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="DSS_Gateway",
        model=None,
        image=dss_service_image,
        position=Position(x=120, y=420),
    )
    dssGateway.icon = "host.gif"
    session.add_link(node1=dssGateway, node2=sInternet, iface1=pInternet.create_iface(dssGateway.id, 0))

    #display provider
    nDisplay = session.add_node(
        next(nodeIds),
        _type=NodeType.DOCKER,
        name="DisplayProvider",
        model=None,
        image="ubuntu:core",
        position=Position(x=80, y=600),
    )
    nDisplay.icon = "host.gif"
    session.add_link(node1=nDisplay, node2=sInternet, iface1=pInternet.create_iface(nDisplay.id, 0))

    # Stadium Nodes
    pStadium = InterfaceHelper(ip4_prefix="10.83.1.0/24")
    sStadium = session.add_node(
        next(nodeIds), _type=NodeType.WIRELESS_LAN, position=Position(x=150, y=300)
    )
    sStadium.set_wlan(
        {
        "range": "280",
        "bandwidth": "55000000",
        "delay": "6000",
        "jitter": "5",
        "error": "5",
        }
    )
    sStadium.icon = "wlan.gif"

    session.add_link(node1=nUSS, node2=sStadium, iface1=pStadium.create_iface(nUSS.id, 0))

    mobility_config = {
            "file": os.path.join(os.path.abspath(os.path.dirname(__file__)), "mobility.ns2"),
            "refresh_ms": "1000",
            "loop": "1",
            "autostart": "0.0",
            "map": "",
            "script_start": "",
            "script_pause": "",
            "script_stop": "",
    }

    sStadium.set_mobility(mobility_config)
    client.set_mobility_config(session.id, sStadium.id, mobility_config)

    drones = []

    ## Interior Drones
    for i in range(5):
        xp = i * 75
        yp = i * 45
        node = session.add_node(
            next(nodeIds),
            _type=NodeType.DOCKER,
            name=f"Interior{i}",
            model=None,
            image=drone_image,
            position=Position(x=xp, y=yp),
        )
        node.icon = "drone38.png"
        session.add_link(node1=node, node2=sStadium, iface1=pStadium.create_iface(node.id, 0))
        drones.append(node)

    # Exterior Drones
    for i in range(5):
        xp = i * 250
        yp = i * 250
        node = session.add_node(
            next(nodeIds),
            _type=NodeType.DOCKER,
            name=f"Exterior{i}",
            model=None,
            image=drone_image,
            position=Position(x=xp, y=yp),
        )
        node.icon = "drone38.png"
        session.add_link(node1=node, node2=sStadium, iface1=pStadium.create_iface(node.id, 0))
        drones.append(node)


    #with client.context_connect():
        
    client.start_session(session)
    mobility_config_now = client.get_mobility_config(session.id, sStadium.id)
    print(session)
    #client.save_xml(session.id, "/home/mcurran2/dss_script.xml")

    print(mobility_config_now)
    for n in session.nodes:
        node = session.nodes[n]
        node_details, interfaces, links = client.get_node(session.id, node.id)
        #print(node_details)
        #print(links)
        #print(interfaces)

    #time.sleep(30000)
    for n in session.nodes:
        node = session.nodes[n]
        #print(node.__dict__)
        if node.geo is None:
            #position = my_session.location.getgeo(node.position.x, node.position.y, node.position.z)
            geo = GeoLocation()
            geo.setrefgeo(session.location.lat, session.location.lon, session.location.alt)
            geo.refscale = 150.0
            position = geo.getgeo(node.position.x, node.position.y, 0.0)
            geo = Geo(lat=position[0], lon=position[1], alt=position[2])
            node.geo = geo
            #print(position)
        

    node_command(oauth, "/usr/bin/dummy-oauth -private_key_file /var/test-certs/auth2.key")
    node_command(cockroach, "cockroach.sh start-single-node --insecure")
    node_command(spDB, "/bin/bash -c '/usr/local/bin/docker-entrypoint.sh mysqld > /proc/1/fd/1 2> /proc/1/fd/2'")
    time.sleep(5)
    node_command(nUSS, "/bin/bash -c 'SERVICE_PROVIDER_DB=10.83.0.3 python uss/manage.py migrate'")
    time.sleep(5)
    node_command(nUSS, "/bin/bash -c 'SERVICE_PROVIDER_DB=10.83.0.3 OAUTH_HOST=10.83.0.5 DSS_HOST=10.83.0.7 python uss/manage.py runserver 0.0.0.0:8000 > /proc/1/fd/1 2> /proc/1/fd/2'")
    time.sleep(3)
    node_command(nDSS, '/bin/bash -c "/usr/bin/db-manager --schemas_dir /db-schemas/rid --db_version latest --cockroach_host 10.83.0.4 > /proc/1/fd/1 2> /proc/1/fd/2"')
    time.sleep(3)
    node_command(nDSS, '/bin/bash -c "/usr/bin/db-manager --schemas_dir /db-schemas/scd --db_version latest --cockroach_host 10.83.0.4 > /proc/1/fd/1 2> /proc/1/fd/2"')
    time.sleep(3)
    node_command(nDSS, "/bin/bash -c '/usr/bin/core-service -cockroach_host 10.83.0.4 -public_key_files /var/test-certs/auth2.pem -reflect_api -log_format console -dump_requests -accepted_jwt_audiences localhost,host.docker.internal,local-gateway,dss_sandbox_local-dss-http-gateway_1 -enable_scd -enable_http > /proc/1/fd/1 2> /proc/1/fd/2'")
    time.sleep(3)
    node_command(dssGateway, "/bin/bash -c '/usr/bin/http-gateway -core-service 10.83.0.6:8081 -addr :8082 -trace-requests -enable_scd > /proc/1/fd/1 2> /proc/1/fd/2'")
    time.sleep(3)

    for d in drones:
        #print(d)
        node_command(d, "/bin/bash -c 'python drone.py 10.83.1.4 > /proc/1/fd/1 2> /proc/1/fd/2'")

if __name__ in ["__main__", "__builtin__"]:
    main()