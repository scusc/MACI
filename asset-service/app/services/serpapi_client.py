"""
SerpAPI Integration Client for Asset Service.
Fetches categorized hotel, vacation rental, event, flight, and local inventory via Google engines.
"""

import logging
import os
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import HTTPException
from maci_core.schemas.asset import AssetCreate

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY", "PLACEHOLDER_KEY")
SERPAPI_BASE_URL = "https://serpapi.com/search.json"

async def search_inventory(
    query: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    category: str = "general"
) -> List[AssetCreate]:
    """Search for properties using SerpAPI's google_hotels engine."""
    if SERPAPI_KEY == "PLACEHOLDER_KEY":
        raise HTTPException(status_code=500, detail="SerpAPI configuration missing in production.")

    params = {
        "engine": "google_hotels", "q": query, "check_in_date": check_in, 
        "check_out_date": check_out, "adults": adults, "currency": "USD", 
        "gl": "us", "hl": "en", "api_key": SERPAPI_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SERPAPI_BASE_URL, params=params, timeout=10.0)
            response.raise_for_status()
            return _parse_hotel_response(response.json(), category)
    except Exception as e:
        logger.error(f"Failed to fetch hotel inventory from SerpAPI: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Upstream SerpAPI error: {str(e)}")

async def search_events(
    query: str,
    location: str,
    category: str = "event"
) -> List[AssetCreate]:
    """Search for events (Concerts, Festivals) using SerpAPI's google_events engine."""
    if SERPAPI_KEY == "PLACEHOLDER_KEY":
        raise HTTPException(status_code=500, detail="SerpAPI configuration missing in production.")

    params = {
        "engine": "google_events", "q": query, "location": location, "api_key": SERPAPI_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SERPAPI_BASE_URL, params=params, timeout=10.0)
            response.raise_for_status()
            return _parse_event_response(response.json(), category)
    except Exception as e:
        logger.error(f"Failed to fetch event inventory from SerpAPI: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Upstream SerpAPI error: {str(e)}")

async def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str = None,
    type: int = 2 # 1=Round, 2=One-way
) -> List[Dict[str, Any]]:
    """Search for flights using SerpAPI's google_flights engine."""
    if SERPAPI_KEY == "PLACEHOLDER_KEY":
        raise HTTPException(status_code=500, detail="SerpAPI configuration missing in production.")
        
    params = {
        "engine": "google_flights", "departure_id": departure_id, "arrival_id": arrival_id,
        "outbound_date": outbound_date, "type": type, "currency": "USD", "hl": "en", 
        "api_key": SERPAPI_KEY
    }
    if return_date and type == 1:
        params["return_date"] = return_date

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SERPAPI_BASE_URL, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data.get("best_flights", [])[:3] # Return top 3 flights
    except Exception as e:
        logger.error(f"Failed to fetch flights from SerpAPI: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Upstream SerpAPI error: {str(e)}")

async def search_local(
    query: str,
    location: str
) -> List[Dict[str, Any]]:
    """Search for local restaurants/places using SerpAPI's google_local engine."""
    if SERPAPI_KEY == "PLACEHOLDER_KEY":
        raise HTTPException(status_code=500, detail="SerpAPI configuration missing in production.")
        
    params = {
        "engine": "google_local", "q": query, "location": location,
        "gl": "us", "hl": "en", "api_key": SERPAPI_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SERPAPI_BASE_URL, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("local_results", [])[:5] # Return top 5 places
    except Exception as e:
        logger.error(f"Failed to fetch local places from SerpAPI: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Upstream SerpAPI error: {str(e)}")

def _parse_hotel_response(data: dict, category: str) -> List[AssetCreate]:
    assets = []
    properties = data.get("properties", [])
    for prop in properties:
        price = prop.get("total_rate", {}).get("extracted_value", 
                prop.get("rate_per_night", {}).get("extracted_value", 500.0) * 3)
        asset_type = prop.get("type", "hotel").lower()
        if "vacation rental" in asset_type: asset_type = "villa"
        media_urls = [img["thumbnail"] if isinstance(img, dict) and "thumbnail" in img else img for img in prop.get("images", []) if isinstance(img, dict) or isinstance(img, str)]
                
        assets.append(AssetCreate(
            title=prop.get("name", "Unknown Property"),
            description=prop.get("description", "A beautiful property."),
            asset_type=asset_type, category=category,
            location=prop.get("gps_coordinates", {}).get("address", "Unknown Location"),
            total_price=float(price), currency="USD", total_slices=4,
            external_reference_id=prop.get("property_token"), media_urls=media_urls
        ))
    return assets

def _parse_event_response(data: dict, category: str) -> List[AssetCreate]:
    assets = []
    events = data.get("events_results", [])
    for event in events:
        price = 500.0 # VIP assumption
        media_urls = [event["thumbnail"]] if "thumbnail" in event else []
        assets.append(AssetCreate(
            title=event.get("title", "Unknown Event"),
            description=event.get("description", "An exclusive event."),
            asset_type="event", category=category,
            location=event.get("address", []).pop(0) if event.get("address") else "Unknown Location",
            total_price=float(price), currency="USD", total_slices=4,
            external_reference_id=event.get("event_id", str(hash(event.get("title")))),
            media_urls=media_urls
        ))
    return assets

