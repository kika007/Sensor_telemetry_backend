import json
import queue
import ssl
import threading
from pathlib import Path

import paho.mqtt.client as mqtt
from pymongo import MongoClient

# Wildcard topic for all sensors
TOPIC = "sensors/+/data"


def db_worker_loop(data_queue: queue.Queue, collection, stop_event: threading.Event) -> None:
    """Background thread that reads from the queue and writes to MongoDB."""
    print("Database worker thread started.")
    
    # Loop continues until the program is shut down
    while not stop_event.is_set() or not data_queue.empty():
        payload = None
        try:
            # Wait for an item in the queue for up to 1 second
            # If nothing comes in 1 second, it throws queue.Empty, and checks stop_event again
            payload = data_queue.get(timeout=1.0)
            
            # Insert the payload into MongoDB safely in the background
            result = collection.insert_one(payload)
            print(f"Successfully saved to MongoDB with ID: {result.inserted_id}")
            
        except queue.Empty:
            # Normal behavior when no new messages are arriving
            continue
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
        finally:
            if payload is not None:
                data_queue.task_done()
            
    print("Database worker thread safely stopped.")


def on_connect(client, userdata, flags, rc, properties=None) -> None:
    """Callback executed when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to the secure MQTT broker.")
        client.subscribe(TOPIC)
        print(f"Listening for messages on wildcard topic: {TOPIC}")
    else:
        print(f"Error connecting to MQTT broker, code: {rc}")


def on_message(client, userdata, msg) -> None:
    """Fast callback that just puts the message into the memory queue."""
    # Retrieve the thread-safe queue from userdata
    data_queue = userdata.get("data_queue")
    
    try:
        payload = json.loads(msg.payload.decode())
        if not isinstance(payload, dict):
            raise ValueError("MQTT payload must be a JSON object")
        payload["source_topic"] = msg.topic
        
        # Put the message in the queue for the background thread to process.
        # This is extremely fast and doesn't block the MQTT network loop.
        data_queue.put_nowait(payload)
        print(f"Added message from '{msg.topic}' to the database queue.")

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        print(f"Error: Invalid payload on topic {msg.topic}: {e}")
    except queue.Full:
        print("Warning: The internal data queue is full. Message dropped!")
    except Exception as e:
        print(f"Error processing message: {e}")


def main() -> None:
    """Load configuration, initialize DB thread, and start MQTT network loop."""
    current_dir = Path(__file__).parent
    config_path = current_dir / "config.json"
    
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return
        
    broker_config = config.get("broker_settings", {})
    db_config = config.get("database_settings", {})

    print("Connecting to MongoDB...")
    mongo_client = MongoClient(db_config.get("mongo_uri"))
    db = mongo_client[db_config.get("db_name")]
    collection = db[db_config.get("collection_name")]

    # Initialize the thread-safe Queue (max 1000 items) and Stop Event
    data_queue = queue.Queue(maxsize=1000)
    stop_event = threading.Event()

    # Start the background database worker thread
    db_thread = threading.Thread(
        target=db_worker_loop, 
        args=(data_queue, collection, stop_event),
        daemon=True
    )
    db_thread.start()

    # Initialize MQTT Client (pass the queue via userdata instead of collection)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, 
        userdata={"data_queue": data_queue}
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.tls_set(ca_certs=broker_config.get("ca_cert"), tls_version=ssl.PROTOCOL_TLSv1_2)

    print("Starting MQTT Network Loop...")
    try:
        client.connect(broker_config.get("host"), broker_config.get("port"), 60)
        client.loop_forever()  
    except KeyboardInterrupt:
        print("\nEnding MQTT worker...")
    finally:
        # Shut down the background database thread safely
        stop_event.set()
        if db_thread.is_alive():
            db_thread.join()
            
        client.disconnect()
        mongo_client.close()
        print("Disconnected from MQTT and MongoDB.")


if __name__ == "__main__":
    main()