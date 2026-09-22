import asyncio

import requests
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartAsyncTcpServer

# Constants
API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=49.1951&longitude=16.6068"
    "&current=temperature_2m,relative_humidity_2m"
)
SERVER_HOST = "localhost"
SERVER_PORT = 5020


async def update_registers(context):
    """
    Periodically fetch data from API and write it to Modbus registers.
    """
    while True:
        try:
            # Added a timeout, which is a good practice for web requests
            response = requests.get(API_URL, timeout=10)
            data = response.json()
            
            # Modbus stores only integers. Multiply temperature by 10
            temp = int(data["current"]["temperature_2m"] * 10)
            humidity = int(data["current"]["relative_humidity_2m"])
            
            # Write to Holding Registers (function code 3, address 0)
            register = context[0]
            register.setValues(3, 0, [temp, humidity]) 
            
            print(
                f"Server updated registers: "
                f"Temp={temp / 10.0}°C, Humidity={humidity}%"
            )
        except Exception as e:
            print(f"Error fetching API data: {e}")
        
        await asyncio.sleep(10)


async def run_server():
    """
    Initialize and start the asynchronous Modbus TCP server.
    """
    store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0, 0]))
    context = ModbusServerContext(slaves=store, single=True)
    
    asyncio.create_task(update_registers(context))
    
    print(f"Starting Modbus TCP Server on {SERVER_HOST}:{SERVER_PORT}...")
    print("Press CTRL+C to stop.")
    
    await StartAsyncTcpServer(
        context=context, address=(SERVER_HOST, SERVER_PORT)
    )


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nShutting down Modbus server...")