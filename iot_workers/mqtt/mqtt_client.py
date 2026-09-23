"""
Universal MQTT Sensor Client Class
Fetches environmental data from an API and publishes it via MQTT.
"""
import json
import ssl
import threading

import paho.mqtt.client as mqtt
import requests


class MQTTSensorClient:
    """A template class representing a single MQTT sensor device."""

    def __init__(self, config_dict: dict, broker_host: str, broker_port: int, ca_cert: str):
        """Initialize the sensor client using a configuration dictionary."""
        self.name = config_dict["name"]
        self.location = config_dict["location"]
        self.api_url = config_dict["api_url"]
        self.data_topic = config_dict["data_topic"]
        self.control_topic = config_dict["control_topic"]
        self.wait_time = config_dict["wait_time"]
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_cert = ca_cert

        # Control flag to pause/resume data fetching via API commands
        self._is_paused = False  
        # Event to safely stop the background publishing thread
        self._stop_event = threading.Event()

        # Initialize the Paho MQTT client securely
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.tls_set(ca_certs=self.ca_cert, tls_version=ssl.PROTOCOL_TLSv1_2)
        
        self.worker_thread = None

    def on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        """Execute when the client receives a CONNACK from the broker."""
        if rc == 0:
            print(f"[{self.name}] Successfully connected. Listening on '{self.control_topic}'.")
            client.subscribe(self.control_topic)
        else:
            print(f"[{self.name}] Connection error, code: {rc}")

    def on_message(self, client, userdata, msg) -> None:
        """Handle incoming control commands (e.g., from Django REST API)."""
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            
            if command == "stop":
                self._is_paused = True
                print(f"[{self.name}] CMD: Stopping data transmission...")
            elif command == "start":
                self._is_paused = False
                print(f"[{self.name}] CMD: Resuming data transmission...")
                
        except json.JSONDecodeError:
            print(f"[{self.name}] Error: Invalid JSON on control topic.")

    def fetch_energy_data(self) -> dict:
        """Fetch current weather data synchronously from the API."""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            current_data = data.get("current", {})
            
            return {
                "location": self.location,
                "solar_radiation_w_m2": current_data.get("direct_radiation", 0.0),
                "wind_speed_kmh": current_data.get("wind_speed_10m", 0.0),
                "timestamp": current_data.get("time", ""),
            }
        except requests.exceptions.RequestException as e:
            print(f"[{self.name}] API fetching error: {e}")
            return {}

    def _publishing_loop(self) -> None:
        """Internal loop running in a background thread."""
        # Loop continues until the stop_event is set
        while not self._stop_event.is_set():
            
            # Fetch and publish data only if the client is not paused
            if not self._is_paused:
                payload = self.fetch_energy_data()
                if payload:
                    json_payload = json.dumps(payload)
                    self.client.publish(self.data_topic, json_payload)
                    print(f"[{self.name}] Published: {json_payload}")
            
            # Wait for the specified time, but wake up immediately if stop_event is set
            self._stop_event.wait(self.wait_time)

    def start(self) -> None:
        """Connect to broker and start the publishing background thread."""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            self.worker_thread = threading.Thread(target=self._publishing_loop)
            self.worker_thread.daemon = True
            self.worker_thread.start()
        except Exception as e:
            print(f"[{self.name}] Failed to start: {e}")

    def stop(self) -> None:
        """Gracefully disconnect the client and stop the background thread."""
        print(f"[{self.name}] Stopping worker thread...")
        
        # Signal the background thread to terminate immediately
        self._stop_event.set()
        
        # Wait up to 2 seconds for the thread to safely finish
        if self.worker_thread is not None and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
            
        # Disconnect the MQTT client
        self.client.loop_stop()
        self.client.disconnect()
        print(f"[{self.name}] Successfully disconnected and stopped.")