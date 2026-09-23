import json
import time
from pathlib import Path

from mqtt_client import MQTTSensorClient

current_dir = Path(__file__).parent
config_path = current_dir / "config.json"


def main() -> None:
    """Read configuration, instantiate clients, and keep the main thread alive."""
    
    # Load the configuration file
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        print("Error: 'config.json' not found. Please create it first.")
        return
    except json.JSONDecodeError:
        print("Error: 'config.json' contains invalid JSON format.")
        return

    broker_settings = config.get("broker_settings", {})
    sensor_configs = config.get("sensors", [])
    
    # List to keep track of all active client objects
    active_clients = []

    # Dynamically create and start clients based on the JSON list
    for sensor_data in sensor_configs:
        client_instance = MQTTSensorClient(
            config_dict=sensor_data,
            broker_host=broker_settings.get("host", "localhost"),
            broker_port=broker_settings.get("port", 8883),
            ca_cert=broker_settings.get("ca_cert", "")
        )
        try:
            client_instance.start()
        except RuntimeError as e:
            print(e)
            continue
        active_clients.append(client_instance)

    # Keep the application running
    try:
        print(f"\nSuccessfully started {len(active_clients)} sensor(s). Press Ctrl+C to stop.\n")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down all sensors...")
    finally:
        for client in active_clients:
            client.stop()


if __name__ == "__main__":
    main()