from django.shortcuts import render
from time import time
from django.utils import timezone
from django.contrib.auth.models import User, Group
from dp.serializers import SubscriptionSerializer, ServiceAreaSerializer
from rest_framework import viewsets
from rest_framework import permissions
from django.http import HttpResponse, JsonResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
import socket
from datetime import datetime, timedelta
import requests
from dp.models import Subscription, ServiceArea, Callbacks, SpatialVolume, Vertices, Flight, FlightState, Position, FlightDetails
import os

class Subscribe(APIView):
    def put(self, request):
        data = JSONParser().parse(request)
        extents = data["extents"]
        time_start = extents["time_start"]
        time_end = extents["time_end"]

        spatial_vol = extents["spatial_volume"]
        alt_hi = spatial_vol["altitude_hi"]
        alt_lo = spatial_vol["altitude_lo"]

        footprint = spatial_vol["footprint"]
        vertices = footprint["vertices"]

        timestamp = timezone.now()

        subscription = Subscription()
        hostname = socket.gethostname()
        subscription.owner = hostname
        subscription.time_end = time_end
        subscription.time_start = time_start
        subscription.save()

        sv = SpatialVolume()
        sv.altitude_hi = alt_hi
        sv.altitude_lo = alt_lo
        sv.subscription = subscription
        sv.save()

        for v in vertices:
            vert = Vertices()
            vert.lng = v["lng"]
            vert.lat = v["lat"]
            vert.spatial_volume = sv
            vert.save()

        auth_host = os.getenv("OAUTH_HOST", "pierce-core-01.crc.nd.edu")
        dss_host = os.getenv("DSS_HOST", "pierce-core-01.crc.nd.edu")

        #serializer = SubscriptionSerializer(data = subscription)
        session = requests.Session()
        response = requests.get("http://" + auth_host + ":8085/token?grant_type=client_credentials&scope=dss.read.identification_service_areas&intended_audience=localhost&issuer=localhost")
        auth_json = response.json()
        access_token = auth_json["access_token"]
        session.headers.update({'Authorization' : 'Bearer ' + access_token})
        id = str(subscription.id)
        url = "http://" + dss_host + ":8082/v1/dss/subscriptions/" + id

        data["callbacks"] = {"identification_service_area_url": "http://"+ hostname + ":8001/dp/uss/identification_service_areas"}
        session_res = session.put(url, json=data)
        r = session_res.json()
        print(r)
        ret_subs = r["subscription"]
        owner = ret_subs["owner"]
        version = ret_subs["version"]
        not_ind = ret_subs["notification_index"]
        subscription.owner = owner
        subscription.version = version
        subscription.notification_index = not_ind
        subscription.save()

        #save any service areas also returned by the API
        service_areas = r["service_areas"]
        for s in service_areas:
            sa_serializer = ServiceAreaSerializer(data=s)

            if sa_serializer.is_valid():
                sa_serializer.save()
            else:
                print(sa_serializer)

        self.poll_service_provider(subscription=subscription)

        return JsonResponse(data=r)

    @staticmethod
    def poll_service_provider(subscription: Subscription):
        # polls each service area provider we have that's still current
        lats = []
        lngs = []
        spatial_volumes = subscription.spatialvolume_set.all()

        for s in spatial_volumes:
            for v in s.vertices_set.all():
                lats.append(v.lat)
                lngs.append(v.lng)

        sorted_lats = sorted(lats)
        sorted_lngs = sorted(lngs)
        least_lat = str(sorted_lats[0])
        greatest_lat = str(sorted_lats[-1])
        least_lng = str(sorted_lngs[0])
        greatest_lng = str(sorted_lngs[-1])
        view = least_lat + "," + greatest_lng + "," + greatest_lat + "," + least_lng
        timestamp = timezone.now()
        service_areas = ServiceArea.objects.filter(time_end__gt=timestamp)

        session = requests.Session()

        for s in service_areas:
            url = s.flights_url + "?view=" + view
            res = session.get(url)
            r = res.json()
            print(r)


class PushISAs(APIView):

    def post(self, request, id):
        print(id)
        data = JSONParser().parse(request)
        #print(data)

        sa_serializer = ServiceAreaSerializer(data=data["service_area"])

        if sa_serializer.is_valid():
            sa_serializer.save()
        else:
            print(sa_serializer)

        extents = data["extents"]
        spatial_vol = extents["spatial_volume"]
        footprint = spatial_vol["footprint"]
        vertices = footprint["vertices"]

        timestamp = timezone.now()
        subscriptions = Subscription.objects.filter(time_end__gt=timestamp)

        # get flight data now that we know about the service provider
        for s in subscriptions:
            Subscribe.poll_service_provider(s)

        return JsonResponse(data=data)

    



class GetFlights(APIView):
    def get(self, request):
        view = request.GET.get('view', '')
        print(view)
        coords = view.split(',')  # ?view=34.122,-118.453,34.125,-118.458