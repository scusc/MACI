import asyncio
import urllib.parse
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from app.services import serpapi_client
from app.api.travel import search_travel, FlightOption

logger = logging.getLogger("rally.travel.api")

class Traveler(BaseModel):
    name: str
    origin: str

class TripLeg(BaseModel):
    destination: str
    arrival_date: str
    departure_date: str

class AIQuoteRequest(BaseModel):
    travelers: List[Traveler]
    itinerary: List[TripLeg]
    budget_tier: str = "balanced"

class TravelerQuote(BaseModel):
    name: str
    origin: str
    flight_route: str
    individual_cost: int
    shared_cost: int
    total_cost: int
    flight_evidence: Optional[str] = None

class AIQuoteResponse(BaseModel):
    shared_cost_per_person: int
    shared_accommodation_name: str
    shared_accommodation_total: int
    hotel_evidence: Optional[str] = None
    traveler_quotes: List[TravelerQuote]
    reasoning: str

async def _fetch_flight(origin: str, destination: str, date: str) -> dict:
    try:
        flights = await serpapi_client.search_flights(
            departure_id=origin.upper(),
            arrival_id=destination.upper(),
            outbound_date=date,
            type=2 # one way
        )
        if flights:
            best = flights[0]
            price = float(best.get("price", 500.0))
            airline = best.get("flights", [{}])[0].get("airline", "Major Carrier")
            return {"price": price, "airline": airline}
    except Exception as e:
        logger.warning(f"Flight search failed {origin}->{destination}: {e}")
    
    return {"price": 450.0, "airline": "Generic Airline"}

async def _fetch_hotel(destination: str, checkin: str, checkout: str, group_size: int, budget: str) -> dict:
    try:
        hotels = await serpapi_client.search_inventory(
            query=f"Villas in {destination}",
            check_in=checkin,
            check_out=checkout,
            adults=group_size,
            category=budget
        )
        if hotels:
            sorted_hotels = sorted(hotels, key=lambda x: x.price_per_night_usd)
            if budget == "budget": h = sorted_hotels[0]
            elif budget == "luxury": h = sorted_hotels[-1]
            else: h = sorted_hotels[len(sorted_hotels)//2]
            
            checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
            checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
            days = max(1, (checkout_d - checkin_d).days)
            
            return {
                "name": h.name,
                "total_price": h.price_per_night_usd * days,
            }
    except Exception as e:
        logger.warning(f"Hotel search failed {destination}: {e}")
        
    checkin_d = datetime.strptime(checkin, "%Y-%m-%d")
    checkout_d = datetime.strptime(checkout, "%Y-%m-%d")
    days = max(1, (checkout_d - checkin_d).days)
    return {"name": f"Generic Group Accommodation in {destination}", "total_price": 250.0 * days * (group_size / 2)}

# We will inject this into travel.py
