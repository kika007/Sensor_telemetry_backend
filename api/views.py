from rest_framework.views import APIView
from rest_framework.response import Response
from pymongo import MongoClient

# Database configuration constants
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
DB_NAME = "db"


class CombinedTelemetryView(APIView):
    """
    View to fetch both Modbus and MQTT data from MongoDB
    and return them combined in a single JSON response.
    """
    def get(self, request):
        # 1. Connect to the MongoDB database
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        # 2. Fetch the latest 10 records from the Modbus collection
        modbus_collection = db["modbus_data"]
        modbus_data = list(modbus_collection.find().sort("_id", -1).limit(10))
        
        # Convert MongoDB ObjectId to string for JSON serialization
        for item in modbus_data:
            item["_id"] = str(item["_id"])

        # 3. Fetch the latest 10 records from the MQTT energy collection
        energy_collection = db["mqtt_data"]
        energy_data = list(energy_collection.find().sort("_id", -1).limit(10))
        
        # Convert MongoDB ObjectId to string for JSON serialization
        for item in energy_data:
            item["_id"] = str(item["_id"])

        # 4. Combine both datasets into a single dictionary
        combined_data = {
            "modbus_telemetry": modbus_data,
            "mqtt_telemetry": energy_data
        }

        # Return the combined data as a JSON response
        return Response(combined_data)
