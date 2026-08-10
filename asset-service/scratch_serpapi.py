import asyncio
import json
import os
from app.services import serpapi_client

async def main():
    try:
        flights = await serpapi_client.search_flights(
            departure_id="JFK",
            arrival_id="CDG",
            outbound_date="2026-10-10",
            type=2
        )
        print("FLIGHTS:")
        print(json.dumps(flights, indent=2))
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
