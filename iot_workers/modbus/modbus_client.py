import ssl
import time
import threading
import queue
from datetime import datetime

from pymodbus.client import ModbusTlsClient
from pymongo import MongoClient


def db_worker_loop(data_queue: queue.Queue, collection, stop_event: threading.Event) -> None:
    """Background thread that safely writes data to MongoDB."""
    print("[DB Worker] Background database writer started.")
    
    while not stop_event.is_set():
        try:
            # Wait for data in the queue for up to 1 second
            payload = data_queue.get(timeout=1.0)
            
            # Safe background insert
            result = collection.insert_one(payload)
            print(f"[DB Worker] Successfully saved to DB, ID: {result.inserted_id}")
            
            # Mark the task as completed
            data_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[DB Worker] Database insert error: {e}")
            
    print("[DB Worker] Database thread safely terminated.")


class ModbusWeatherClient:
    """Object-oriented Modbus Client."""

    def __init__(self, host: str, port: int, ca_cert: str, mongo_uri: str, db_name: str, collection_name: str, wait_time: int = 5):
        self.host = host
        self.port = port
        self.ca_cert = ca_cert
        self.wait_time = wait_time
        
        # Database configuration
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        
        # Thread and queue management
        self.data_queue = queue.Queue(maxsize=1000)
        self.stop_event = threading.Event()
        self.db_thread = None
        
        # TLS context preparation
        ssl_context = ssl.create_default_context(cafile=self.ca_cert)
        ssl_context.check_hostname = False
        
        # Client initialization (not connected yet)
        self.modbus_client = ModbusTlsClient(host=self.host, port=self.port, sslctx=ssl_context)

    def _reading_loop(self) -> None:
        """Main loop for reading Modbus registers."""
        while not self.stop_event.is_set():
            
            # 1. Connection check
            if not self.modbus_client.is_socket_open():
                print("[Modbus Client] Connecting to server...")
                try:
                    if not self.modbus_client.connect():
                        print(f"[Modbus Client] Connection failed. Retrying in {self.wait_time}s...")
                        self.stop_event.wait(self.wait_time)
                        continue
                except Exception as e:
                    print(f"[Modbus Client] Connection error: {e}")
                    self.stop_event.wait(self.wait_time)
                    continue

            # 2. Reading data from the server (with a safety net)
            try:
                result = self.modbus_client.read_holding_registers(address=1, count=2, device_id=1)
                
                if not result.isError():
                    temp = result.registers[0] / 10.0
                    humidity = result.registers[1]
                    
                    data = {
                        "protocol": "Modbus TLS",
                        "location": "Brno",
                        "temperature_c": temp,
                        "humidity_percent": humidity,
                        "timestamp": datetime.now().isoformat(),
                    }
                    
                    # FAST SOLUTION: Just put the data into the queue and move on
                    self.data_queue.put(data)
                    print(f"[Modbus Client] Read from server -> Temp: {temp}°C, Humidity: {humidity}% (Sent to queue)")
                else:
                    print(f"[Modbus Client] Error reading registers: {result}")
                    
            except Exception as e:
                print(f"[Modbus Client] Communication error: {e}")
                self.modbus_client.close()
            
            # Wait safely before the next cycle
            self.stop_event.wait(self.wait_time)

    def start(self) -> None:
        """Starts the database thread and the main reading loop."""
        mongo_client = MongoClient(self.mongo_uri)
        collection = mongo_client[self.db_name][self.collection_name]
        
        # Start the background database worker
        self.db_thread = threading.Thread(
            target=db_worker_loop, 
            args=(self.data_queue, collection, self.stop_event),
            daemon=True
        )
        self.db_thread.start()
        
        print("[Modbus Client] Starting data collection...")
        try:
            self._reading_loop()
        except KeyboardInterrupt:
            print("\n[Modbus Client] Shutdown command received (Ctrl+C)...")
        finally:
            self.stop()
            mongo_client.close()

    def stop(self) -> None:
        """Safely and cleanly terminates all threads and connections."""
        self.stop_event.set()
        
        if self.db_thread and self.db_thread.is_alive():
            self.db_thread.join(timeout=2.0)
            
        self.modbus_client.close()
        print("[Modbus Client] Successfully and cleanly shut down.")


if __name__ == "__main__":
    # Temporarily hardcoded for testing, later we will load this from config.json
    client_app = ModbusWeatherClient(
        host="localhost",
        port=8020,
        ca_cert="./mosquitto/config/certs/ca.crt",
        mongo_uri="mongodb://root:rootpassword@localhost:27017/",
        db_name="db",
        collection_name="modbus_data"
    )
    client_app.start()