import json
import ssl
from pathlib import Path

import paho.mqtt.client as mqtt
from pymongo import MongoClient

# Using wildcard '+' to subscribe to all sensors (e.g., sensors/brno/data, sensors/prague/data)
TOPIC = "sensors/+/data" 


def on_connect(client, userdata, flags, rc, properties=None) -> None:
    """Callback executed when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to the secure MQTT broker.")
        client.subscribe(TOPIC)
        print(f"Listening for messages on wildcard topic: {TOPIC}")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")


def on_message(client, userdata, msg) -> None:
    """Callback executed when a message is received."""
    # Retrieve the database collection safely from userdata
    collection = userdata.get("db_collection")
    
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received data from '{msg.topic}'")

        # Inject the topic name into the payload
        payload["source_topic"] = msg.topic

        # Insert into MongoDB
        result = collection.insert_one(payload)
        print(f"Successfully saved to MongoDB with ID: {result.inserted_id}\n")

    except json.JSONDecodeError:
        print(f"Error: Received invalid JSON format on topic {msg.topic}")
    except Exception as e:
        print(f"Error processing and saving message: {e}")


def main() -> None:
    """Load configuration, initialize DB, configure TLS, and start blocking loop."""
    
    # Load configuration from config.json
    current_dir = Path(__file__).parent
    config_path = current_dir / "config.json"
    
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        print(f"Error: 'config.json' not found at {config_path}")
        return
        
    broker_config = config.get("broker_settings", {})
    db_config = config.get("database_settings", {})

    # Initialize MongoDB connection
    print("Connecting to MongoDB...")
    mongo_client = MongoClient(db_config.get("mongo_uri"))
    db = mongo_client[db_config.get("db_name")]
    collection = db[db_config.get("collection_name")]

    # Initialize MQTT Client
    # We pass the collection in a dictionary as userdata
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, 
        userdata={"db_collection": collection}
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Apply secure TLS configuration dynamically
    client.tls_set(
        ca_certs=broker_config.get("ca_cert"), 
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    print("Starting MQTT Worker...")
    try:
        client.connect(
            broker_config.get("host"), 
            broker_config.get("port"), 
            60
        )
        client.loop_forever()  
    except KeyboardInterrupt:
        print("\nEnding MQTT worker...")
        client.disconnect()
        mongo_client.close()
        print("Disconnected from MQTT broker and MongoDB.")


if __name__ == "__main__":
    main()