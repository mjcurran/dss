from django.contrib.auth.models import User, Group
from rest_framework import serializers
from sp.models import ServiceArea, Subscriber, Subscription, Flight, FlightDetails, FlightState, Vertices, SpacialVolume, Position


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        exclude = ['created_at', 'updated_at']

class SpacialVolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacialVolume
        exclude = ['created_at', 'updated_at']

class VerticesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vertices
        exclude = ['created_at', 'updated_at']

class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        exclude = ['created_at', 'updated_at']

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        exclude = ['created_at', 'updated_at']



class FlightDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightDetails
        exclude = ['created_at', 'updated_at']


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        exclude = ['created_at', 'updated_at', 'id', 'flight_state']

class FlightStateSerializer(serializers.ModelSerializer):
    position = PositionSerializer(many=False, source='current_position')
    
    class Meta:
        model = FlightState
        exclude = ['created_at', 'updated_at', 'flight_id', 'id', 'current_position']

class FlightSerializer(serializers.ModelSerializer):
    current_state = FlightStateSerializer()
    id = serializers.CharField(source='flight_id')

    class Meta:
        model = Flight
        depth = 1
        exclude = ['created_at', 'updated_at', 'flight_id', 'timestamp']
