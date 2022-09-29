from django.db import models
import uuid
from django.utils import timezone


class BusinessModel(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if self.created_at:
            pass
        else:
            self.created_at = timezone.now()

        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class ServiceArea(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    owner = models.CharField(max_length=255, blank=True, default='')
    flights_url = models.CharField(max_length=700, blank=True, default='')
    time_end = models.DateTimeField(auto_now_add=False)
    time_start = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=700, blank=True, default='')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

class Subscriber(BusinessModel):
    url = models.TextField()
    id = models.UUIDField(primary_key=True, default = uuid.uuid4, editable=False)
    service_area = models.ForeignKey('ServiceArea', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

class Subscription(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    subscription_id = models.UUIDField(default = uuid.uuid4, editable=False)
    notification_index = models.IntegerField(default=0, blank=True, null=True)
    subscriber = models.ForeignKey('Subscriber', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    

class SpacialVolume(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    altitude_lo = models.IntegerField(blank=True, null=True)
    altitude_hi = models.IntegerField(blank=True, null=True)
    service_area = models.ForeignKey('ServiceArea', models.DO_NOTHING, blank=True, null=True)

class Vertices(BusinessModel):
    id = models.UUIDField(primary_key=True, default = uuid.uuid4, editable=False)
    lng = models.FloatField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    spacial_volume = models.ForeignKey('SpacialVolume', models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

class FlightState(BusinessModel):
    #{"timestamp": "2022-09-21T15:32:06.372930+00:00", "operational_status": "Airborne", "position":Position, "height": Height, 
    # "track": 181.6975641099569, "speed": 4.91, "timestamp_accuracy": 0.0, "speed_accuracy": "SA3mps", "vertical_speed": 0.0}
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    timestamp = models.DateTimeField()
    operational_status = models.CharField(max_length=255, blank=True, default='')
    track = models.CharField(max_length=255, blank=True, default='')
    speed = models.CharField(max_length=255, blank=True, default='')
    timestamp_accuracy = models.CharField(max_length=255, blank=True, default='')
    speed_accuracy = models.CharField(max_length=255, blank=True, default='')
    vertical_speed = models.CharField(max_length=255, blank=True, default='')
    current_position = models.ForeignKey('Position', models.DO_NOTHING, blank=True, null=True)
    flight_id = models.ForeignKey('Flight', models.DO_NOTHING, blank=True, null=True)

class Position(BusinessModel):
    #{"lat": 46.9754225199202, "lng": 7.475076017275803, "alt": 620.0, "accuracy_h": "HAUnkown", "accuracy_v": "VAUnknown", "extrapolated": false}
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    lng = models.FloatField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    alt = models.FloatField(blank=True, null=True)
    accuracy_h = models.CharField(max_length=255, blank=True, default='')
    accuracy_v = models.CharField(max_length=255, blank=True, default='')
    extrapolated = models.BooleanField(default=False)
    flight_state = models.ForeignKey('FlightState', models.DO_NOTHING, blank=True, null=True)
    time = models.DateTimeField()

class Flight(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    flight_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    aircraft_type = models.CharField(max_length=255, blank=True, default = 'NotDeclared')
    current_state = models.ForeignKey('FlightState', models.DO_NOTHING, blank=True, null=True)
    simulated = models.BooleanField(default=False)
    timestamp = models.DateTimeField()

class Location(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    ng = models.FloatField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    

class FlightDetails(BusinessModel):
    id = models.UUIDField(primary_key = True, default = uuid.uuid4, editable = False)
    #details_id = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    flight = models.ForeignKey('Flight', models.DO_NOTHING, blank=True, null=True)
    operator_description = models.TextField()
    operator_id = models.CharField(max_length=255)
    operator_location = models.ForeignKey('Location', models.DO_NOTHING, blank=True, null=True)
    registration_number = models.CharField(max_length=700, blank=True, default='')
    serial_number = models.CharField(max_length=700, blank=True, default='')
