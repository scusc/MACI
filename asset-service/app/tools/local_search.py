"""
Local Search Tool — LangChain @tool wrapper for SerpAPI Google Local + Google Events.

Used by the Activity Agent to find restaurants, attractions, museums, and events
at the destination to build a shared group itinerary.
"""

import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.serp_client import SerpClient

logger = logging.getLogger("maci.tools.local_search")


class LocalSearchInput(BaseModel):
    """Input schema for local place/attraction search."""

    query: str = Field(description="Search query (e.g., 'best restaurants in Barcelona', 'museums near Sagrada Familia')")
    location: Optional[str] = Field(default=None, description="City or area to focus the search (e.g., 'Barcelona, Spain')")
    limit: int = Field(default=5, description="Maximum number of results to return (1-10)")


class EventSearchInput(BaseModel):
    """Input schema for local event search."""

    query: str = Field(description="Event search query (e.g., 'concerts in Barcelona July 2026', 'festivals near me')")
    location: Optional[str] = Field(default=None, description="City or area to focus the search")


def _extract_local_results(raw: dict, max_results: int = 5) -> list[dict]:
    """Parse Google Local results."""
    places = []
    for p in (raw.get("local_results") or [])[:max_results]:
        places.append({
            "name": p.get("title"),
            "rating": p.get("rating"),
            "reviews_count": p.get("reviews"),
            "type": p.get("type"),
            "address": p.get("address"),
            "hours": p.get("hours"),
            "phone": p.get("phone"),
            "website": p.get("website"),
            "gps": p.get("gps_coordinates"),
            "thumbnail": p.get("thumbnail"),
        })
    return places


def _extract_events(raw: dict, max_results: int = 5) -> list[dict]:
    """Parse Google Events results."""
    events = []
    for e in (raw.get("events_results") or [])[:max_results]:
        events.append({
            "title": e.get("title"),
            "date": e.get("date", {}).get("start_date") if isinstance(e.get("date"), dict) else e.get("date"),
            "venue": e.get("venue", {}).get("name") if isinstance(e.get("venue"), dict) else e.get("venue"),
            "address": e.get("address", []),
            "description": e.get("description"),
            "link": e.get("link"),
            "thumbnail": e.get("thumbnail"),
        })
    return events


def create_local_search_tool(client: SerpClient):
    """Factory that creates a local places search tool bound to a SerpClient."""

    @tool("search_places", args_schema=LocalSearchInput)
    def search_places(
        query: str,
        location: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """Search for local places like restaurants, attractions, museums, and activities.
        Use natural queries like 'best tapas restaurants in Barcelona' or 'museums near Gothic Quarter'."""

        params = {
            "q": query,
            "hl": "en",
            "gl": "us",
        }
        if location:
            params["location"] = location

        logger.info("Searching places: '%s' (location=%s)", query, location)
        raw = client.search("google_local", params)
        places = _extract_local_results(raw, max_results=min(limit, 10))

        return json.dumps({
            "query": query,
            "places_found": len(places),
            "results": places,
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return search_places


def create_event_search_tool(client: SerpClient):
    """Factory that creates an events search tool bound to a SerpClient."""

    @tool("search_events", args_schema=EventSearchInput)
    def search_events(
        query: str,
        location: Optional[str] = None,
    ) -> str:
        """Search for local events like concerts, festivals, conferences, and shows.
        Use queries like 'events in Barcelona July 2026' or 'music festivals Spain summer'."""

        params = {
            "q": query,
            "hl": "en",
            "gl": "us",
        }
        if location:
            params["location"] = location

        logger.info("Searching events: '%s' (location=%s)", query, location)
        raw = client.search("google_events", params)
        events = _extract_events(raw)

        return json.dumps({
            "query": query,
            "events_found": len(events),
            "results": events,
            "calls_remaining": client.calls_remaining,
        }, indent=2)

    return search_events
