from time import time
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from sp.models import ServiceArea, Subscriber, Subscription, SpacialVolume, Vertices, Flight, FlightDetails, FlightState, Position
from sp.serializers import UserSerializer, GroupSerializer, FlightSerializer, FlightDetailsSerializer, FlightStateSerializer, PositionSerializer
import socket
from datetime import datetime, timedelta
import requests


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class FlightsInArea(APIView):
    def get(self, request):
        include_recent_positions = request.GET.get('include_recent_positions', False)
        view = request.GET.get('view', '')
        print(view)
        coords = view.split(',')  # ?view=34.122,-118.453,34.125,-118.458
        #demo code to start with
        flights = Flight.objects.all()
        # TODO add filtering
        #flights = Flight.objects.filter()
        serializer = FlightSerializer(flights, many=True)
        flight_data = serializer.data
        res = {"flights": flight_data}
        timestamp = timezone.now().isoformat()
        res["timestamp"] = timestamp
        #return Response(serializer.data)
        return JsonResponse(data=res)


class InjectFlight(APIView):

    def purge_old_data(self):
        timestamp = timezone.now() - timedelta(minutes=15)
        # TODO delete records older than 15 minutes

    def put(self, request):
        data = JSONParser().parse(request)
        injected_flights = []
        for fl in data["requested_flights"]:
            flight = Flight()
            flight.timestamp = timezone.now()
            injection_id = fl["injection_id"]
            details_resp = fl["details_responses"]
            telemetry = fl["telemetry"]
            if len(details_resp) > 0:
                first_dets = details_resp[0]["details"]
                flight.flight_id = first_dets["id"]
                details = FlightDetails()
                operator_id = first_dets["operator_id"]
                operation_description = first_dets["operation_description"]
                details.operator_id = operator_id
                details.operator_description = operation_description
                flight.save()
                details.flight = flight
                details.save()
                injected_flights.append(flight)
            
            for tel in telemetry:
                timestamp = tel["timestamp"]
                time_acc = tel["timestamp_accuracy"]
                op_status = tel["operational_status"]
                track = tel["track"]
                speed = tel["speed"]
                speed_acc = tel["speed_accuracy"]
                vertical_speed = tel["vertical_speed"]
                flight_state = FlightState()
                flight_state.timestamp = timestamp
                flight_state.flight_id = flight
                flight_state.operational_status = op_status
                flight_state.timestamp_accuracy = time_acc
                flight_state.track = track
                flight_state.speed = speed
                flight_state.speed_accuracy = speed_acc
                flight_state.vertical_speed = vertical_speed
                flight_state.save()
                #position = Position()
                flight.current_state = flight_state
                flight.save()
                flight_pos = tel["position"]
                flight_pos["flight_state"] = flight_state.id
                flight_pos["time"] = timestamp
                pos_ser = PositionSerializer(data=flight_pos)
                
                if pos_ser.is_valid():
                    pos_ser.save()
                else:
                    print(pos_ser)

                self.create_service_area(tel)

        serializer = FlightSerializer(injected_flights, many=True)
        return Response(serializer.data)


    def create_service_area(self, flight_state):
        #{"timestamp": "2022-09-21T15:32:06.372930+00:00", "operational_status": "Airborne", "position": 
        # {"lat": 46.9754225199202, "lng": 7.475076017275803, "alt": 620.0, "accuracy_h": "HAUnkown", "accuracy_v": "VAUnknown", "extrapolated": false}, 
        # "height": {"distance": 50.0, "reference": "TakeoffLocation"}, "track": 181.6975641099569, "speed": 4.91, "timestamp_accuracy": 0.0, 
        # "speed_accuracy": "SA3mps", "vertical_speed": 0.0}
        hostname = socket.gethostname()
        flights_url = hostname + "/sp/v1/uss/flights"

        service_area = ServiceArea()
        service_area.owner = hostname
        service_area.flights_url = flights_url
        service_area.time_start = timezone.now()
        service_area.time_end = service_area.time_start + timedelta(minutes=5)
        version = service_area.time_start.strftime("%m%d%Y%H%M%S")
        service_area.version = version
        service_area.save()

        spacial_vol = SpacialVolume()

        position = flight_state["position"]
        lat_center = position["lat"]
        lng_center = position["lng"]
        alt_center = position["alt"]

        alt_hi = alt_center + 1000
        alt_low = alt_center / 2
        spacial_vol.altitude_hi = alt_hi
        spacial_vol.altitude_lo = alt_low
        spacial_vol.service_area = service_area
        spacial_vol.save()

        n_lat = lat_center + 0.01
        s_lat = lat_center - 0.01
        e_lng = lng_center + 0.01
        w_lng = lng_center - 0.01
        ne = Vertices()
        ne.lat = n_lat
        ne.lng = e_lng
        ne.spacial_volume = spacial_vol
        nw = Vertices()
        nw.lat = n_lat
        nw.lng = w_lng
        nw.spacial_volume = spacial_vol
        sw = Vertices()
        sw.lat = s_lat
        sw.lng = w_lng
        sw.spacial_volume = spacial_vol
        se = Vertices()
        se.lat = s_lat
        se.lng = e_lng
        se.spacial_volume = spacial_vol
        nw.save()
        ne.save()
        sw.save()
        se.save()

        session = requests.Session()
        response = requests.get("http://pierce-core-01.crc.nd.edu:8085/token?grant_type=client_credentials&sub=uss1&intended_audience=host.docker.internal&issuer=dummy&scope=dss.write.identification_service_areas rid.inject_test_data")
        auth_json = response.json()
        access_token = auth_json["access_token"]
        session.headers.update({'Authorization' : 'Bearer ' + access_token})
        id = str(service_area.id)
        print(id)
        url = "http://pierce-core-01.crc.nd.edu:8082/v1/dss/identification_service_areas/" + id
        print(url)
        body = {}
        footprint = {}
        footprint["vertices"] = []
        #footprint["vertices"].append({"lng": ne.lng, "lat": ne.lat})
        footprint["vertices"].append({"lng": nw.lng, "lat": nw.lat})
        footprint["vertices"].append({"lng": se.lng, "lat": se.lat})
        footprint["vertices"].append({"lng": sw.lng, "lat": sw.lat})
        spac = {"footprint": footprint, "altitude_lo": alt_low, "altitude_hi": alt_hi}
        start_time = service_area.time_start.isoformat()
        end_time = service_area.time_end.isoformat()
        extents = {"spatial_volume": spac, "time_start": start_time, "time_end": end_time}
        body["extents"] = extents
        body["flights_url"] = "http://pierce-core-01.crc.nd.edu:8071/mock/ridsp/v1/uss/flights"
        print(body)
        session_res = session.put(url, json=body)
        r = session_res.json()
        print(r)
        #{'service_area': {'flights_url': 'http://pierce-core-01.crc.nd.edu:8071/mock/ridsp/v1/uss/flights', 
        # 'id': 'e8158e0d-6c8e-4eb9-b8b4-a5e2daa4fda7', 'owner': 'uss1', 'time_end': '2022-09-28T17:57:57.635822Z', 
        # 'time_start': '2022-09-28T17:52:57.635934Z', 'version': '1e68nls566qi0'}, 
        # 'subscribers': [{'subscriptions': [{'notification_index': 5, 'subscription_id': '72602f34-e22d-450f-9ba0-b93acc67449d'}], 
        # 'url': 'http://pierce-core-01.crc.nd.edu:8082/v1/dss/isas'}]}
        ret_service_area = r["service_area"]
        version = ret_service_area["version"]
        service_area.version = version  # version is used later for updating the service area
        service_area.save()

        subscribers = r["subscribers"]
        for s in subscribers:
            subscriptions = s["subscriptions"]
            sub_url = s["url"]

            subscriber = Subscriber()
            subscriber.url = sub_url
            subscriber.service_area = service_area
            subscriber.save()
            for ss in subscriptions:
                subscription = Subscription()
                subscription.subscriber = subscriber
                subscription.subscription_id = ss["subscription_id"]
                subscription.notification_index = ss["notification_index"]
                subscription.save()



        

        


