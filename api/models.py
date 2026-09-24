import uuid

from django.db import models

# Create your models here.

class SensorDevice(models.Model):
    """
    Metadata model for IoT sensors stored in PostgreSQL.
    The actual telemetry data from these sensors goes to MongoDB.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)                      # e.g., "Brno-Sensor"
    location = models.CharField(max_length=100, unique=True)     # e.g., "brno"
    api_url = models.URLField(max_length=500, blank=True)
    data_topic = models.CharField(max_length=200)                # e.g., "sensors/brno/data"
    control_topic = models.CharField(max_length=200)             # e.g., "sensors/brno/control"
    wait_time = models.IntegerField(default=10)                  # Refresh interval in seconds
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.location})"
