import os
import json
import psutil
import logging
import time

from core.emulator.coreemu import CoreEmu
from core.emulator.data import IpPrefixes, NodeOptions
from core.emulator.enumerations import EventTypes
from core.nodes.docker import DockerNode
from core.nodes.network import SwitchNode, WlanNode
from core.location.mobility import BasicRangeModel, Ns2ScriptedMobility

def main():

    logging.basicConfig(level=logging.DEBUG)

    mariadb_image =  "uss-sp-mariadb"
    mongodb_image =  "pierce-mongo"
    api_image =  "uss-sp-api"
    nginx_image =  "pierce-nginx"
    drone_image =  "python-drone"
    cockroach_image = "cockroachdb/cockroach:latest"
    dss_service_image = "interuss-test"
    auth_image = "core-oauth"

    coreemu = globals().get("coreemu", CoreEmu())
    session = coreemu.create_session()
    session.set_state(EventTypes.CONFIGURATION_STATE)
    session.options.set_config("controlnet", "172.16.0.0/24")

    # Internal Nodes
    node_mariadb = session.add_node(
        DockerNode,
        options=NodeOptions(
            name="mariadb", model=None, image=mariadb_image, x=100, y=300
        ),
    )
    node_mongodb = session.add_node(
        DockerNode,
        options=NodeOptions(
            name="mongodb", model=None, image=mongodb_image, x=200, y=300
        ),
    )
    sBackend = session.add_node(SwitchNode, options=NodeOptions(x=150, y=250))
    node_api = session.add_node(
        DockerNode,
        options=NodeOptions(name="app", model=None, image=api_image, x=150, y=200),
    )

    cockroach = session.add_node(DockerNode, options=NodeOptions(name="cockroach", model=None, image=cockroach_image, x=300, y=400))
    auth_node = session.add_node(DockerNode, options=NodeOptions(name="dummy_oauth", model=None, image=auth_image, x=300, y=400))
    dss_service = session.add_node(DockerNode, options=NodeOptions(name="dss_core", model=None, image=dss_service_image, x=350, y=450))
    dss_gateway = session.add_node(DockerNode, options=NodeOptions(name="dss_gateway", model=None, image=dss_service_image, x=375, y=375))

    pApp = IpPrefixes(ip4_prefix="10.83.0.0/24")
    session.add_link(node_mongodb.id, sBackend.id, pApp.create_iface(node_mongodb))
    session.add_link(node_mariadb.id, sBackend.id, pApp.create_iface(node_mariadb))
    session.add_link(node_api.id, sBackend.id, pApp.create_iface(node_api)) # 10.83.0.4
    session.add_link(cockroach.id, sBackend.id, pApp.create_iface(cockroach)) # 10.83.0.5
    session.add_link(dss_service.id, sBackend.id, pApp.create_iface(dss_service)) # 10.83.0.7
    session.add_link(dss_gateway.id, sBackend.id, pApp.create_iface(dss_gateway)) # 10.83.0.8
    session.add_link(auth_node.id, sBackend.id, pApp.create_iface(auth_node)) # 10.83.0.6

    # Wlan
    pTransmitter = IpPrefixes(ip4_prefix="10.83.2.0/24")
    sTransmitter = session.add_node(SwitchNode, options=NodeOptions(x=275, y=100))

    session.add_link(node_api.id, sTransmitter.id, pTransmitter.create_iface(node_api))

    # Frontend Nodes
    pFrontend = IpPrefixes(ip4_prefix="10.83.1.0/24")
    node_nginx = session.add_node(
        DockerNode,
        options=NodeOptions(name="nginx", model=None, image=nginx_image, x=150, y=100),
    )
    session.add_link(
        node_nginx.id,
        node_api.id,
        pFrontend.create_iface(node_nginx),
        pFrontend.create_iface(node_api),
    )
    session.add_link(
        node_nginx.id, sTransmitter.id, pTransmitter.create_iface(node_nginx)
    )

    # Setup Mobile Transmitters
    drones = []
    for i in range(5):
        node_drone = session.add_node(
            DockerNode,
            options=NodeOptions(
                name="node_" + str(i + 1),
                model=None,
                image=drone_image,
                x=(275 + (i % 5) * 75),
                y=(200 + int(i / 5.0) * 75),
            ),
        )
        session.add_link(
            node_drone.id, sTransmitter.id, pTransmitter.create_iface(node_drone)
        )
        drones.append(node_drone)

    # instantiate
    session.instantiate()

    if True:
        auth_node.client.check_cmd("/usr/bin/dummy-oauth -private_key_file /var/test-certs/auth2.key", wait=False)
        cockroach.client.check_cmd("cockroach.sh start-single-node --insecure", wait=False)
        time.sleep(3)

        #node_api.client.check_cmd("/bin/bash -c 'export SERVICE_PROVIDER_DB=10.83.0.1'", wait=True)
        #node_api.client.check_cmd("/bin/bash -c 'export OAUTH_HOST=10.83.0.8'", wait=True)
        #node_api.client.check_cmd("/bin/bash -c 'export DSS_HOST=10.83.0.7'", wait=True)

        node_mariadb.client.check_cmd(
            "/bin/bash -c '/usr/local/bin/docker-entrypoint.sh mysqld > /proc/1/fd/1 2> /proc/1/fd/2'",
            wait=False,
        )
        node_mongodb.client.check_cmd(
            "/bin/bash -c '/usr/local/bin/docker-entrypoint.sh mongod > /proc/1/fd/1 2> /proc/1/fd/2'",
            wait=False,
        )
        #set up our database tables
        time.sleep(15)
        node_api.client.check_cmd("/bin/bash -c 'SERVICE_PROVIDER_DB=10.83.0.1 python uss/manage.py migrate'", wait=True )
        node_api.client.check_cmd(
            "/bin/bash -c 'SERVICE_PROVIDER_DB=10.83.0.1 OAUTH_HOST=10.83.0.6 DSS_HOST=10.83.0.8 python uss/manage.py runserver 0.0.0.0:8000 > /proc/1/fd/1 2> /proc/1/fd/2'", wait=False
        )
        node_nginx.client.check_cmd(
            "/bin/bash -c '/docker-entrypoint.sh nginx > /proc/1/fd/1 2> /proc/1/fd/2'",
            wait=False,
        )
        

        dss_service.client.check_cmd('/bin/bash -c "/usr/bin/db-manager --schemas_dir /db-schemas/rid --db_version latest --cockroach_host 10.83.0.5 > /proc/1/fd/1 2> /proc/1/fd/2"', wait=True)
        time.sleep(3)
        dss_service.client.check_cmd('/bin/bash -c "/usr/bin/db-manager --schemas_dir /db-schemas/scd --db_version latest --cockroach_host 10.83.0.5 > /proc/1/fd/1 2> /proc/1/fd/2"', wait=True)
        time.sleep(3)
        dss_service.client.check_cmd("/bin/bash -c '/usr/bin/core-service -cockroach_host 10.83.0.5 -public_key_files /var/test-certs/auth2.pem -reflect_api -log_format console -dump_requests -accepted_jwt_audiences localhost,host.docker.internal,local-gateway,dss_sandbox_local-dss-http-gateway_1 -enable_scd -enable_http > /proc/1/fd/1 2> /proc/1/fd/2'", wait=False)
        time.sleep(3)
        dss_gateway.client.check_cmd("/bin/bash -c '/usr/bin/http-gateway -core-service 10.83.0.7:8081 -addr :8082 -trace-requests -enable_scd > /proc/1/fd/1 2> /proc/1/fd/2'", wait=False)
        time.sleep(5)
        for i in range(len(drones)):
            drones[i].client.check_cmd(
                "/bin/bash -c 'python drone.py 10.83.2.4 > /proc/1/fd/1 2> /proc/1/fd/2'", wait=False
            )

    input("press enter to shutdown")
    coreemu.shutdown()



if __name__ in ["__main__", "__builtin__"]:
    main()