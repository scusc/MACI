"""
Hotel Search Tool — LangChain @tool wrapper for SerpAPI Google Hotels.

Used by the Hotel Agent after flight convergence to find
group-friendly accommodation at the destination.
"""

import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.serp_client import SerpClient

logger = logging.getLogger("maci.tools.hotel_search")


class HotelSearchInput(BaseModel):
    """Input schema for hotel search. The LLM uses this to construct the API call."""

    destination: str = Field(description="City or area to search hotels in (e.g., 'Barcelona, Spain')")
    check_in_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    adults: int = Field(default=2, description="Number of adult guests")
    min_rating: Optional[float] = Field(default=None, description="Minimum star rating (e.g., 3, 4, 4.5)")
    max_price: Optional[int] = Field(default=None, description="Maximum nightly price in the selected currency")
    currency: str = Field(default="USD", description="Currency for prices")


def _extract_hotel_options(raw: dict, max_results: int = 5) -> list[dict]:
    """Parse the raw SerpAPI Google Hotels response into clean options."""
    hotels = []
    properties = (raw.get("properties") or [])[:max_results]

    for h in properties:
        # Extract the best price from the prices array
        prices = h.get("prices") or [{}]
        best_price = prices[0] if prices else {}

        hotels.append({
            "name": h.get("name"),
            "overall_rating": h.get("overall_rating"),
            "reviews_count": h.get("reviews"),
            "hotel_class": h.get("hotel_class"),
            "description": h.get("description"),
            "check_in_time": h.get("check_in_time"),
            "check_out_time": h.get("check_out_time"),
            "price_per_night": h.get("rate_per_night", {}).get("lowest"),
            "total_price": h.get("total_rate", {}).get("lowest"),
            "booking_source": best_price.get("source"),
            "booking_link": best_price.get("link"),
            "amenities": h.get("amenities", [])[:10],  # Top 10 amenities
            "nearby_places": [
                {"name": p.get("name"), "walking_min": p.get("transportations", [{}])[0].get("duration") if p.get("transportations") else None}
                for p in (h.get("nearby_places") or [])[:3]
            ],
            "images": [img.get("thumbnail") for img in (h.get("images") or [])[:3]],
        })

    return hotels


def create_hotel_search_tool(client: SerpClient):
    """Factory that creates a hotel search tool bound to a specific SerpClient instance."""

    @tool("search_hotels", args_schema=HotelSearchInput)
    def search_hotels(
        destination: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 2,
        min_rating: Optional[float] = None,
        max_price: Optional[int] = None,
        currency: str = "USD",
    ) -> str:
        """Search hotels at a destination for specific dates.
        Returns up to 5 hotels with prices, ratings, amenities, and booking links.
        Use city names like 'Barcelona, Spain' or 'Tokyo, Japan'."""

        params = {
            "q": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "currency": currency,
            "gl": "us",
            "hl": "en",
        }

        if min_rating and min_rating >= 4:
            params["hotel_class"] = int(min_rating)
        if max_price:
            params["max_price"] = max_price

        logger.info("Searching hotels in '%s' (%s to %s)", destination, check_in_date, check_out_date)
        raw = client.search("google_hotels", params)

        options = _extract_hotel_options(raw)

        return json.dumps({
            "destination": destination,
            "dates": f"{check_in_date} → {check_out_date}",
            "hotels_found": len(options),
            "options": options,
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return search_hotels
