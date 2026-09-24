import json
import ssl
import paho.mqtt.client as mqtt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from .models import SensorDevice  

# Database configuration constants
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
DB_NAME = "db"
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 8883
MQTT_CONTROL_TOPIC = "sensor/control/brno"
CA_CERT = "./mosquitto/config/certs/ca.crt"


class CombinedTelemetryView(APIView):
    """
    View to fetch both Modbus and MQTT data from MongoDB
    and return them combined in a single JSON response.
    """
    def get(self, request):
        # Connect to the MongoDB database
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # Fetch the latest 10 records from the Modbus collection
        modbus_collection = db["modbus_data"]
        modbus_data = list(modbus_collection.find().sort("_id", -1).limit(10))
        
        # Convert MongoDB ObjectId to string for JSON serialization
        for item in modbus_data:
            item["_id"] = str(item["_id"])

        # Fetch the latest 10 records from the MQTT collection
        mqtt_collection = db["mqtt_data"]
        mqtt_data = list(mqtt_collection.find().sort("_id", -1).limit(10))
        
        # Convert MongoDB ObjectId to string for JSON serialization
        for item in mqtt_data:
            item["_id"] = str(item["_id"])

        # Combine both datasets into a single dictionary
        combined_data = {
            "modbus_telemetry": modbus_data,
            "mqtt_telemetry": mqtt_data
        }

        # Return the combined data as a JSON response
        return Response(combined_data)
    

# Fallback configuration (can also be moved to settings.py as MQTT_FALLBACK_SENSORS)
FALLBACK_SENSORS = [
    {
        "name": "Brno-Sensor",
        "location": "brno",
        "api_url": "https://api.open-meteo.com/v1/forecast?latitude=49.1951&longitude=16.6068&current=wind_speed_10m,direct_radiation",
        "data_topic": "sensors/brno/data",
        "control_topic": "sensors/brno/control",
        "wait_time": 10,
        "is_active": True,
    },
    {
        "name": "Prague-Sensor",
        "location": "prague",
        "api_url": "https://api.open-meteo.com/v1/forecast?latitude=50.0880&longitude=14.4208&current=wind_speed_10m,direct_radiation",
        "data_topic": "sensors/prague/data",
        "control_topic": "sensors/prague/control",
        "wait_time": 12,
        "is_active": True,
    }
]

class MQTTControlView(APIView):
    """
    API View to remotely control the MQTT workers using PostgreSQL metadata,
    with a robust fallback to config-defined sensors if the database is empty.
    """

    def _get_active_sensor_map(self):
        """
        Helper method to retrieve a dictionary of active sensors: {location_lower: control_topic}.
        Prioritizes database records; falls back to config defaults if the database is empty.
        """
        # 1. Fetch active sensors from PostgreSQL
        db_sensors = SensorDevice.objects.filter(is_active=True)
        sensor_map = {sensor.location.lower(): sensor.control_topic for sensor in db_sensors}

        # 2. Fall back to config if no records are found in the database
        if not sensor_map:
            for fallback in FALLBACK_SENSORS:
                if fallback.get("is_active", True):
                    loc = fallback["location"].lower()
                    if loc not in sensor_map:
                        sensor_map[loc] = fallback["control_topic"]
        
        return sensor_map

    def get(self, request):
        sensor_map = self._get_active_sensor_map()
        available_locations = list(sensor_map.keys())
        
        return Response(
            {
                "info": "Send a POST request with {'command': 'start'/'stop', 'targets': ['target1', 'target2']} to control the MQTT workers.",
                "available_targets": available_locations
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        # 1. Extract data from the incoming request
        command = request.data.get("command")
        targets = request.data.get("targets", [])
        
        # 2. Validate the command
        if command not in ["start", "stop"]:
            return Response(
                {"error": "Invalid command. Please use 'start' or 'stop'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not isinstance(targets, list) or len(targets) == 0:
            return Response(
                {"error": "Please provide a list of 'targets' (e.g., ['brno'] or ['all'])."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Fetch active sensors (DB records with config fallback)
        sensor_map = self._get_active_sensor_map()
        
        # Normalize targets to lowercase
        normalized_targets = [str(t).lower() for t in targets]
        
        # 4. Filter targets against our available sensor records
        if "all" in normalized_targets:
            valid_targets = list(sensor_map.keys())
        else:
            valid_targets = [t for t in normalized_targets if t in sensor_map]
            
        if not valid_targets:
            return Response(
                {"error": f"No valid targets found. Available active sensors are: {list(sensor_map.keys())}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Initialize the MQTT client
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        try:
            # Connect securely using TLS settings
            client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            
            payload = json.dumps({"command": command})
            published_details = []

            # 6. Iterate and publish commands using topics from the map
            for target in valid_targets:
                topic = sensor_map[target]
                client.publish(topic, payload)
                
                published_details.append({
                    "location": target,
                    "topic": topic
                })
            
            # Disconnect gracefully after publishing
            client.disconnect()
            
            return Response(
                {
                    "message": f"Command '{command}' sent successfully via MQTT.",
                    "details": published_details
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Failed to connect to MQTT broker: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )