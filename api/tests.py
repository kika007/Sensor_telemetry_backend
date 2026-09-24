from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import SensorDevice


class TelemetryEndpointTests(APITestCase):
    """Basic tests for our API endpoints."""

    def test_get_telemetry_returns_200_ok(self):
        """Verify that the telemetry reading endpoint returns a successful 200 OK status."""
        url = reverse('all_telemetry')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MQTTControlEndpointTests(APITestCase):
    """Tests for the dynamic MQTT control endpoint."""

    def test_post_valid_command_returns_200_ok(self):
        """Verify that sending a valid command and targets list returns 200 OK."""
        SensorDevice.objects.create(
            name="Test sensor Brno", 
            location="brno", 
            data_topic="sensors/brno/data", 
            control_topic="sensors/brno/control",
            is_active=True
        )
        
        url = reverse('control_mqtt')
        data = {
            "command": "stop",
            "targets": ["brno"]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_post_missing_target_returns_400_bad_request(self):
        """Verify that missing the 'targets' parameter results in a 400 Bad Request."""
        url = reverse('control_mqtt')
        data = {
            "command": "stop"
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
