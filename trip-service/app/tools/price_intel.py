"""
Price Intelligence Tool — LangChain @tool wrappers for flight deals + price insights.

These tools power MACI's proactive price intelligence:
  - "Prices are LOW right now, book within 48 hours!"
  - "Flights from JFK→BCN just dropped 23% below typical"
  - Historical price trend data for informed group decisions
"""

import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.serp_client import SerpClient

logger = logging.getLogger("maci.tools.price_intel")


class PriceInsightsInput(BaseModel):
    """Input schema for price insights (historical trends)."""

    departure_id: str = Field(description="3-letter IATA departure airport code")
    arrival_id: str = Field(description="3-letter IATA arrival airport code")
    outbound_date: str = Field(description="Departure date YYYY-MM-DD")
    return_date: Optional[str] = Field(default=None, description="Return date YYYY-MM-DD")
    currency: str = Field(default="USD", description="Currency for prices")


class FlightDealsInput(BaseModel):
    """Input schema for flight deals (discounted destinations from an origin)."""

    departure_id: str = Field(description="3-letter IATA airport code to find deals FROM")
    outbound_date: Optional[str] = Field(default=None, description="Departure date or range (YYYY-MM-DD or YYYY-MM-DD,YYYY-MM-DD)")
    return_date: Optional[str] = Field(default=None, description="Return date or range")
    max_price: Optional[int] = Field(default=None, description="Maximum price filter")
    stops: int = Field(default=0, description="0=Any, 1=Nonstop, 2=1 stop max")


def create_price_insights_tool(client: SerpClient):
    """Creates a price insights tool for historical trend analysis."""

    @tool("get_price_insights", args_schema=PriceInsightsInput)
    def get_price_insights(
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: Optional[str] = None,
        currency: str = "USD",
    ) -> str:
        """Get historical price trend data for a specific route.
        Returns whether current prices are low/typical/high compared to historical norms,
        plus the typical price range. Use this to advise the group on optimal booking timing."""

        params = {
            "departure_id": departure_id.upper(),
            "arrival_id": arrival_id.upper(),
            "outbound_date": outbound_date,
            "type": 1 if return_date else 2,
            "currency": currency,
            "hl": "en",
            "gl": "us",
        }
        if return_date:
            params["return_date"] = return_date

        logger.info("Getting price insights: %s → %s", departure_id, arrival_id)
        raw = client.search("google_flights", params)

        insights = raw.get("price_insights", {})
        return json.dumps({
            "route": f"{departure_id}→{arrival_id}",
            "date": outbound_date,
            "lowest_price": insights.get("lowest_price"),
            "price_level": insights.get("price_level"),  # "low", "typical", or "high"
            "typical_price_range": insights.get("typical_price_range"),
            "price_history": insights.get("price_history", [])[-10:],  # Last 10 data points
            "recommendation": _generate_recommendation(insights),
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return get_price_insights


def create_flight_deals_tool(client: SerpClient):
    """Creates a deals scanner tool for finding discounted destinations."""

    @tool("find_flight_deals", args_schema=FlightDealsInput)
    def find_flight_deals(
        departure_id: str,
        outbound_date: Optional[str] = None,
        return_date: Optional[str] = None,
        max_price: Optional[int] = None,
        stops: int = 0,
    ) -> str:
        """Find heavily discounted flight deals from a specific airport.
        Returns destinations with current vs average prices and discount percentages.
        Use this to suggest budget-friendly alternatives to the group."""

        params = {
            "departure_id": departure_id.upper(),
            "stops": stops,
            "hl": "en",
            "gl": "us",
            "currency": "USD",
        }
        if outbound_date:
            params["outbound_date"] = outbound_date
        if return_date:
            params["return_date"] = return_date
        if max_price:
            params["max_price"] = max_price

        logger.info("Scanning deals from %s", departure_id)
        raw = client.search("google_flights_deals", params)

        deals = []
        for d in (raw.get("deals") or [])[:8]:
            deals.append({
                "destination": d.get("name"),
                "country": d.get("country"),
                "price": d.get("price"),
                "average_price": d.get("average_price"),
                "discount_percent": d.get("discount_percentage"),
                "airport_code": d.get("arrival_airport_code"),
                "dates": f"{d.get('start_date')} → {d.get('end_date')}",
                "flight_link": d.get("flight_link"),
            })

        return json.dumps({
            "origin": departure_id,
            "deals_found": len(deals),
            "deals": deals,
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return find_flight_deals


def _generate_recommendation(insights: dict) -> str:
    """Generate a human-readable booking recommendation from price insights."""
    level = insights.get("price_level", "unknown")
    if level == "low":
        return "⚡ BOOK NOW — Prices are below historical norms. This is a good time to buy."
    elif level == "typical":
        return "📊 Prices are normal for this route. Safe to book or wait a few days."
    elif level == "high":
        return "⏳ WAIT — Prices are above average. Consider waiting or shifting dates by a few days."
    else:
        return "No historical data available for this route."
