import time
from datetime import datetime

from pymodbus.client import ModbusTcpClient
from pymongo import MongoClient

# Constants for database and server connection
MONGO_URI = "mongodb://root:rootpassword@localhost:27017/"
DB_NAME = "iot_db"
COLLECTION_NAME = "modbus_data"
SERVER_HOST = "localhost"
SERVER_PORT = 5020
WAIT_TIME = 5


def run_client():
    """
    Connect to Modbus server, read registers, and save data to MongoDB.
    """
    mongo_client = MongoClient(MONGO_URI)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]
    
    modbus_client = ModbusTcpClient(SERVER_HOST, port=SERVER_PORT)
    
    print("Starting Modbus TCP Client. Press CTRL+C to stop.")
    
    try:
        while True:
            if modbus_client.connect():
                result = modbus_client.read_holding_registers(
                    address=0, count=2, slave=1
                )
                
                if not result.isError():
                    temp = result.registers[0] / 10.0
                    humidity = result.registers[1]
                    
                    data = {
                        "protocol": "Modbus TCP",
                        "location": "Brno",
                        "temperature_c": temp,
                        "humidity_percent": humidity,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    
                    db_result = collection.insert_one(data)
                    print(
                        f"Saved to DB (ID: {db_result.inserted_id}) | "
                        f"Temp: {temp}°C, Humidity: {humidity}%"
                    )
                else:
                    print("Error reading Modbus registers.")
                
                modbus_client.close()
            else:
                print(f"Failed to connect to Modbus server on {SERVER_PORT}.")
            
            time.sleep(WAIT_TIME)
            
    except KeyboardInterrupt:
        print("\nShutting down Modbus client...")
        modbus_client.close()


if __name__ == "__main__":
    run_client()