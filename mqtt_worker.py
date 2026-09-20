import json
import paho.mqtt.client as mqtt
from pymongo import MongoClient

BROKER_HOST = "localhost"  
Broker_PORT = 1883
TOPIC = "sensor/energy/brno"

# MongoDB Configuration
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["db"]  
collection = db["energy_data"]

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Successfully connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"Listening for messages on topic: {TOPIC}")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")
        
        

def on_message(client, userdata, msg):
    
    payload_str = msg.payload.decode('utf-8')
    print(f"\nReceived message: {payload_str}")
    
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received message on topic '{msg.topic}': {payload}")
        
        # Insert the received data into MongoDB
        result = collection.insert_one(payload)
        print(f"Successfully saved to database with ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"Error processing message: {e}")
        
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, Broker_PORT, 60)

print("Starting MQTT worker...")
try:
    client.loop_forever()  
except KeyboardInterrupt:
    print("\nEnding MQTT worker...")
    client.disconnect()
    print("Disconnected from MQTT broker")