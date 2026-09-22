import json
import ssl

import paho.mqtt.client as mqtt
from pymongo import MongoClient

# MQTT & MongoDB Configuration
BROKER_HOST = "localhost"
BROKER_PORT = 8883
TOPIC = "sensor/energy/brno"
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
DB_NAME = "db"
COLLECTION_NAME = "mqtt_data"
CA_CERT = "./mosquitto/config/certs/ca.crt"

# Initialize MongoDB client and collection
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]


def on_connect(client, userdata, flags, rc, properties=None) -> None:
    """Callback function executed when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to the MQTT broker.")
        client.subscribe(TOPIC)
        print(f"Listening for messages on topic: {TOPIC}")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")


def on_message(client, userdata, msg) -> None:
    """Callback function executed when a message is received on a subscribed topic."""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received message on topic '{msg.topic}': {payload}")

        # Insert the received payload into MongoDB
        result = collection.insert_one(payload)
        print(f"Successfully saved to database with ID: {result.inserted_id}")

    except Exception as e:
        print(f"Error processing message: {e}")


def run_mqtt_worker() -> None:
    """Initialize MQTT subscriber client, configure TLS, and start blocking loop."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)

    print("Starting MQTT worker...")
    
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        client.loop_forever()  # Blocking network loop
    except KeyboardInterrupt:
        print("\nEnding MQTT worker...")
        client.disconnect()
        print("Disconnected from MQTT broker.")


if __name__ == "__main__":
    run_mqtt_worker()