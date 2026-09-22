import ssl
import time
from datetime import datetime

from pymodbus.client import ModbusTlsClient
from pymongo import MongoClient

# Modbus TLS Client Configuration
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
DB_NAME = "db"
COLLECTION_NAME = "modbus_data"
SERVER_HOST = "localhost"
SERVER_PORT = 8020
WAIT_TIME = 5
CA_CERT = "./mosquitto/config/certs/ca.crt"


def run_client() -> None:
    """Connect securely to the Modbus TLS server, read registers,

    handle connection drops gracefully, and save data to MongoDB.
    """
    mongo_client = MongoClient(MONGO_URI)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]

    ssl_context = ssl.create_default_context(cafile=CA_CERT)
    ssl_context.check_hostname = False

    modbus_client = ModbusTlsClient(
        host=SERVER_HOST,
        port=SERVER_PORT,
        sslctx=ssl_context,
    )

    print("Starting modern Modbus TLS Client.")

    try:
        while True:
            # Check if socket is open; if not, try to reconnect
            if not modbus_client.is_socket_open():
                print("Connection lost. Trying to reconnect...")
                try:
                    if not modbus_client.connect():
                        print(
                            f"Failed to connect on port {SERVER_PORT}. "
                            f"Retrying in {WAIT_TIME}s..."
                        )
                        time.sleep(WAIT_TIME)
                        continue
                    print("Successfully reconnected to the Modbus TLS server!")
                except Exception as e:
                    print(f"Connection error: {e}. Retrying later...")
                    time.sleep(WAIT_TIME)
                    continue

            # Read registers with runtime exception handling
            try:
                result = modbus_client.read_holding_registers(
                    address=1, count=2, device_id=1
                )

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

                    # Write the data to MongoDB
                    db_result = collection.insert_one(data)
                    print(
                        f"Saved to DB (ID: {db_result.inserted_id}) | "
                        f"Temp: {temp}°C, Humidity: {humidity}%"
                    )
                else:
                    print(f"Error reading Modbus registers: {result}")

            except Exception as e:
                print(f"Runtime communication error: {e}")
                # Force close socket on error to ensure a clean reconnect next cycle
                try:
                    modbus_client.close()
                except Exception:
                    pass

            # Wait before the next read cycle
            time.sleep(WAIT_TIME)

    except KeyboardInterrupt:
        print("\nShutting down Modbus client...")
    finally:
        # Securely close the connection to the Modbus server
        modbus_client.close()


if __name__ == "__main__":
    run_client()