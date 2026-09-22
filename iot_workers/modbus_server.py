import asyncio
import ssl

import requests
from pymodbus.server import ModbusTlsServer
from pymodbus.simulator import SimDevice, SimData, DataType

# Modbus TLS Server Configuration
API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=49.1951&longitude=16.6068"
    "&current=temperature_2m,relative_humidity_2m"
)
SERVER_HOST = "localhost"
SERVER_PORT = 8020
CERT_FILE = "./mosquitto/config/certs/server.crt"
KEY_FILE = "./mosquitto/config/certs/server.key"


async def update_registers(server):
    """
    Periodically fetch data from API and write it to Modbus registers using async_setValues.
    """
    # Initial wait to ensure server is fully up before first API call
    await asyncio.sleep(2)
    
    while True:
        try:
            response = requests.get(API_URL, timeout=10)
            data = response.json()
            
            # we could also use 2 registers for decimal values instead of multiplying by 10
            temp = int(data["current"]["temperature_2m"] * 10)
            humidity = int(data["current"]["relative_humidity_2m"])
            
            # 1 = device_id, 3 = func_code (Holding Registers), 1 = address, [temp, humidity] = values
            await server.async_setValues(1, 3, 1, [temp, humidity])
            
            print(
                f"Server updated registers: "
                f"Temp={temp / 10.0}°C, Humidity={humidity}%"
            )
        except Exception as e:
            print(f"Error fetching API data: {e}")
        
        await asyncio.sleep(10)


async def run_server():
    """
    Initialize and start the Modbus TLS server. (PyModbus v4-ready)
    """
    device = SimDevice(
        id=1, 
        simdata=[SimData(address=1, values=[0, 0], datatype=DataType.REGISTERS)]
    )
    
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    
    print(f"Starting Modbus TLS Server on {SERVER_HOST}:{SERVER_PORT}...")
    
    # Iinitialization of the instance of the ModbusTlsServer
    server = ModbusTlsServer(
        context=device,
        address=(SERVER_HOST, SERVER_PORT),
        sslctx=ssl_context,
    )
    
   # Start the background task to update registers periodically
    asyncio.create_task(update_registers(server))
    
    # Ruuuuun
    await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nShutting down Modbus TLS server...")