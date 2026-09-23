import json
import ssl
import time

import paho.mqtt.client as mqtt
import requests

# MQTT Publisher Configuration
BROKER_HOST = "localhost"
BROKER_PORT = 8883
TOPIC = "sensor/energy/brno"
# Topic specifically for receiving commands
CONTROL_TOPIC = "sensor/control/brno"
WAIT_TIME = 10
CA_CERT = "./mosquitto/config/certs/ca.crt"

API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=49.1951&longitude=16.6068"
    "&current=wind_speed_10m,direct_radiation"
)

# Global flag to control the data publishing loop
is_running = True


def fetch_energy_data() -> dict | None:
    """Fetch current weather data from API synchronously."""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        current_data = data.get("current", {})
        
        return {
            "location": "Brno",
            "solar_radiation_w_m2": current_data.get("direct_radiation", 0.0),
            "wind_speed_kmh": current_data.get("wind_speed_10m", 0.0),
            "timestamp": current_data.get("time", ""),
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def on_connect(client, userdata, flags, rc, properties=None) -> None:
    """Execute when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to the MQTT broker.")
        client.subscribe(CONTROL_TOPIC)
        print(f"Listening for control commands on '{CONTROL_TOPIC}'...")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")


def on_message(client, userdata, msg) -> None:
    """Handle incoming commands from Django API."""
    global is_running
    
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        
        if command == "stop":
            is_running = False
            print("\n[COMMAND RECEIVED] Stopping data transmission...")
        elif command == "start":
            is_running = True
            print("\n[COMMAND RECEIVED] Resuming data transmission...")
            
    except json.JSONDecodeError:
        print("Error: Received invalid JSON payload on control topic.")


def run_mqtt_client() -> None:
    """Initialize client, connect securely, and manage publishing."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    
    # Assign our new on_message function to handle incoming commands
    client.on_message = on_message  
    
    client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)

    print("Starting synchronous MQTT TLS Client with remote control.")

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        # Handles network traffic and callbacks in the background
        client.loop_start()  
        
        while True:
            if is_running:
                payload = fetch_energy_data()

                if payload:
                    json_payload = json.dumps(payload)
                    client.publish(TOPIC, json_payload)
                    print(f"Sent to '{TOPIC}': {json_payload}")
            else:
                print("Client is paused. Waiting for 'start' command...")

            time.sleep(WAIT_TIME)

    except KeyboardInterrupt:
        print("\nShutting down MQTT client...")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT broker.")


if __name__ == "__main__":
    run_mqtt_client()
