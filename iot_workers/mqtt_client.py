import json
import ssl
import time

import paho.mqtt.client as mqtt
import requests

# MQTT Publisher Configuration
BROKER_HOST = "localhost"
BROKER_PORT = 8883
TOPIC = "sensor/energy/brno"
API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=49.1951&longitude=16.6068"
    "&current=wind_speed_10m,direct_radiation"
)
WAIT_TIME = 10
CA_CERT = "./mosquitto/config/certs/ca.crt"


def fetch_energy_data() -> dict | None:
    """Fetch current weather/energy data from Open-Meteo API."""
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
    """Callback function executed when the client connects to the broker."""
    if rc == 0:
        print("Successfully connected to the MQTT broker.")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")


def run_mqtt_client() -> None:
    """Initialize MQTT client, connect securely, and publish data periodically."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLSv1_2)

    print("Starting modern MQTT TLS Client.")

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        client.loop_start()  # Start background thread for network traffic
        
        while True:
            payload = fetch_energy_data()

            if payload:
                json_payload = json.dumps(payload)
                client.publish(TOPIC, json_payload)
                print(f"Sent to topic '{TOPIC}': {json_payload}")

            time.sleep(WAIT_TIME)

    except KeyboardInterrupt:
        print("\nShutting down MQTT client...")
    finally:
        # Stop background loop and disconnect
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT broker.")


if __name__ == "__main__":
    run_mqtt_client()
