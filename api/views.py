import json
import ssl
import paho.mqtt.client as mqtt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient

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
    
class MQTTControlView(APIView):
    """
    API View to remotely control the MQTT worker.
    Accepts POST requests with {"command": "start"} or {"command": "stop"}.
    """
    def get(self, request):
        return Response(
            {"info": "Send a POST request with {'command': 'start'} or {'command': 'stop'} to control the MQTT worker."},
            status=status.HTTP_200_OK
        )
    def post(self, request):
        # Extract the command from the incoming web request
        command = request.data.get("command")
        
        # Validate the command
        if command not in ["start", "stop"]:
            return Response(
                {"error": "Invalid command. Please use 'start' or 'stop'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize the MQTT client to send the command
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        try:
            # Connect securely using the same TLS settings
            client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            
            # Format the payload and publish to the control topic
            payload = json.dumps({"command": command})
            client.publish(MQTT_CONTROL_TOPIC, payload)
            
            # Disconnect gracefully
            client.disconnect()
            
            return Response(
                {"message": f"Command '{command}' sent successfully via MQTT."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to connect to MQTT broker: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
