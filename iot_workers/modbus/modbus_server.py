import asyncio
import ssl
import requests
from pymodbus.server import ModbusTlsServer
from pymodbus.simulator import SimDevice, SimData, DataType

class ModbusWeatherServer:

    def __init__(self, host: str, port: int, cert_file: str, key_file: str, api_url: str):
        self.host = host
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file
        self.api_url = api_url
        self.server = None

    async def fetch_weather_data(self) -> dict:
        """Fetch API data safely without blocking the asyncio event loop."""
        # asyncio.to_thread runs the synchronous requests.get in a background thread
        response = await asyncio.to_thread(requests.get, self.api_url, timeout=10)
        response.raise_for_status()
        return response.json()

    async def update_registers_loop(self) -> None:
        """Background task to periodically update Modbus registers."""
        # Initial wait to ensure server is fully up
        await asyncio.sleep(2)
        
        while True:
            try:
                data = await self.fetch_weather_data()
                
                # Multiply by 10 to store one decimal place in an integer register
                temp = int(data["current"]["temperature_2m"] * 10)
                humidity = int(data["current"]["relative_humidity_2m"])
                
                # 1=DeviceID, 3=HoldingRegisters, 1=Address
                await self.server.async_setValues(1, 3, 1, [temp, humidity])
                
                print(f"[Modbus Server] Updated registers -> Temp: {temp / 10.0}°C, Humidity: {humidity}%")
            
            except Exception as e:
                print(f"[Modbus Server] API fetch error: {e}")
            
            # Wait 10 seconds before fetching again
            await asyncio.sleep(10)

    async def start(self) -> None:
        """Initialize and start the Modbus TLS server."""
        # Setup simulated device with 2 holding registers starting at address 1
        device = SimDevice(
            id=1, 
            simdata=[SimData(address=1, values=[0, 0], datatype=DataType.REGISTERS)]
        )
        
        # Setup TLS configuration
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
        
        self.server = ModbusTlsServer(
            context=device,
            address=(self.host, self.port),
            sslctx=ssl_context,
        )
        
        # Start our data-fetching loop in the background
        asyncio.create_task(self.update_registers_loop())
        
        print(f"[Modbus Server] Running on {self.host}:{self.port} with TLS...")
        await self.server.serve_forever()


# Main execution block
if __name__ == "__main__":
    # Temporarily hardcoded for testing, later we will load this from config.json
    API_URL = "https://api.open-meteo.com/v1/forecast?latitude=49.1951&longitude=16.6068&current=temperature_2m,relative_humidity_2m"
    
    server_app = ModbusWeatherServer(
        host="localhost",
        port=8020,
        cert_file="./mosquitto/config/certs/server.crt",
        key_file="./mosquitto/config/certs/server.key",
        api_url=API_URL
    )
    
    try:
        asyncio.run(server_app.start())
    except KeyboardInterrupt:
        print("\n[Modbus Server] Shutting down cleanly...")