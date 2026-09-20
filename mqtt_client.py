import time
import json
import requests
import paho.mqtt.client as mqtt
import ssl


# MQTT Configuration
BROKER_HOST = "localhost"
BROKER_PORT = 8883
TOPIC = "sensor/energy/brno"
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=49.1951&longitude=16.6068&current=wind_speed_10m,direct_radiation"


def fetch_energy_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        current_data = data.get("current", {})
        return {
            "location": "Brno",
            "solar_radiation_w_m2": current_data.get("direct_radiation", 0.0),
            "wind_speed_kmh": current_data.get("wind_speed_10m", 0.0),
            "timestamp": current_data.get("time", "")
        }
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
    
def on_connect(client, userdata, flags, rc, properties=None): #callback function for when the client connects to the broker
    if rc == 0:
        print("Successfully connected to MQTT broker")
    else:
        print(f"Error connecting to MQTT broker, error code: {rc}")
        

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)    
client.on_connect = on_connect
client.tls_set(ca_certs="./mosquitto/config/certs/ca.crt", tls_version=ssl.PROTOCOL_TLSv1_2)

client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_start() #parallel thread to handle network traffic and callbacks
print("Starting download data...")

try:
    while True:
        payload = fetch_energy_data()
        
        if payload:
            json_payload = json.dumps(payload)
            client.publish(TOPIC, json_payload)
            print(f"Sent to topic '{TOPIC}': {json_payload}")
            
        time.sleep(10)
        
except KeyboardInterrupt:
    print("\nEnding MQTT client...")
    client.loop_stop()
    client.disconnect()
    print("Disconnected from MQTT broker")
