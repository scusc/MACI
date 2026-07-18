"""
Flight Search Tool — LangChain @tool wrapper for SerpAPI Google Flights.

This is the primary tool the AI Delegates use to search real-time flights.
It wraps the SerpAPI google_flights engine and returns structured results
that the LLM can reason over.

Reference spec: /SerpAPI specs for flights/flight_search.yaml
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.serp_client import SerpClient

logger = logging.getLogger("maci.tools.flight_search")


class FlightSearchInput(BaseModel):
    """Input schema for the flight search tool. The LLM sees this schema
    and knows exactly what JSON to generate when it wants to call the tool."""

    departure_id: str = Field(description="3-letter IATA airport code for departure (e.g., SFO, JFK, ORD)")
    arrival_id: str = Field(description="3-letter IATA airport code for arrival (e.g., BCN, LHR, NRT)")
    outbound_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(default=None, description="Return date in YYYY-MM-DD format. Omit for one-way.")
    adults: int = Field(default=1, description="Number of adult passengers (1-9)")
    travel_class: int = Field(default=1, description="1=Economy, 2=Premium Economy, 3=Business, 4=First")
    stops: int = Field(default=0, description="0=Any, 1=Nonstop only, 2=1 stop max, 3=2 stops max")
    max_price: Optional[int] = Field(default=None, description="Maximum price filter in USD")
    currency: str = Field(default="USD", description="Currency for prices")


class FlightOption(BaseModel):
    """Structured output for a single flight option."""
    price: Optional[int] = None
    total_duration_min: Optional[int] = None
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    stops: int = 0
    departure_token: Optional[str] = None
    booking_token: Optional[str] = None


def _extract_flight_options(raw: dict, max_results: int = 5) -> list[dict]:
    """Parse the raw SerpAPI response into clean flight options."""
    options = []
    all_flights = (raw.get("best_flights") or []) + (raw.get("other_flights") or [])

    for f in all_flights[:max_results]:
        segments = f.get("flights") or []
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}

        options.append({
            "price": f.get("price"),
            "total_duration_min": f.get("total_duration"),
            "airline": first_seg.get("airline"),
            "flight_number": first_seg.get("flight_number"),
            "departure_airport": first_seg.get("departure_airport", {}).get("id"),
            "departure_time": first_seg.get("departure_airport", {}).get("time"),
            "arrival_airport": last_seg.get("arrival_airport", {}).get("id"),
            "arrival_time": last_seg.get("arrival_airport", {}).get("time"),
            "stops": len(segments) - 1,
            "layovers": [
                {
                    "airport": lay.get("name"),
                    "duration_min": lay.get("duration"),
                }
                for lay in (f.get("layovers") or [])
            ],
            "carbon_emissions_kg": (f.get("carbon_emissions") or {}).get("this_flight"),
            "departure_token": f.get("departure_token"),
            "booking_token": f.get("booking_token"),
        })

    return options


def create_flight_search_tool(client: SerpClient):
    """Factory that creates a flight search tool bound to a specific SerpClient instance."""

    @tool("search_flights", args_schema=FlightSearchInput)
    def search_flights(
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        travel_class: int = 1,
        stops: int = 0,
        max_price: Optional[int] = None,
        currency: str = "USD",
    ) -> str:
        """Search real-time flights between two airports on specific dates.
        Returns up to 5 flight options with prices, durations, airlines, and booking tokens.
        Use IATA airport codes (e.g., SFO, JFK, BCN, LHR)."""

        params = {
            "departure_id": departure_id.upper(),
            "arrival_id": arrival_id.upper(),
            "outbound_date": outbound_date,
            "type": 1 if return_date else 2,  # 1=round trip, 2=one way
            "adults": min(adults, 9),
            "travel_class": travel_class,
            "stops": stops,
            "currency": currency,
            "hl": "en",
            "gl": "us",
        }
        if return_date:
            params["return_date"] = return_date
        if max_price:
            params["max_price"] = max_price

        logger.info("Searching flights: %s → %s on %s", departure_id, arrival_id, outbound_date)
        raw = client.search("google_flights", params)

        options = _extract_flight_options(raw)
        price_insights = raw.get("price_insights", {})

        import json
        return json.dumps({
            "route": f"{departure_id}→{arrival_id}",
            "date": outbound_date,
            "flights_found": len(options),
            "price_insights": {
                "lowest_price": price_insights.get("lowest_price"),
                "price_level": price_insights.get("price_level"),
                "typical_range": price_insights.get("typical_price_range"),
            },
            "options": options,
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return search_flights
