"""
AI Output Schemas — Pydantic models for LangGraph structured outputs.

These models define the exact JSON structure that the LLMs must generate
during the multi-agent trip coordination process. The frontend UI will parse
these models directly.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

# ── Flight Delegate Output ────────────────────────────────────────────────

class FlightSegment(BaseModel):
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    airline: str
    flight_number: str
    duration_min: int

class FlightProposal(BaseModel):
    """Output of the Flight Delegate for a single origin."""
    origin_airport: str = Field(description="The 3-letter IATA code of the departure airport")
    total_price_usd: int = Field(description="Total price in USD for this flight")
    total_duration_min: int = Field(description="Total duration including layovers")
    segments: List[FlightSegment] = Field(description="The flight segments")
    booking_token: Optional[str] = Field(default=None, description="SerpAPI booking token")
    reasoning: str = Field(description="Why this flight was chosen based on the traveler's constraints")

class DelegateResponse(BaseModel):
    """The complete response from a single Flight Delegate."""
    origin_airport: str
    proposals: List[FlightProposal] = Field(description="Top 3 flight proposals, ordered by preference")

# ── Convergence Node Output ────────────────────────────────────────────────

class ConvergedItinerary(BaseModel):
    """Output of the deterministic Convergence Node."""
    is_successful: bool = Field(description="True if a valid convergence window was found for all origins")
    convergence_window_start: Optional[str] = Field(description="Local arrival time window start (ISO8601)")
    convergence_window_end: Optional[str] = Field(description="Local arrival time window end (ISO8601)")
    total_group_flight_cost: int = Field(description="Sum of all selected flights")
    selected_flights: List[FlightProposal] = Field(description="The single best flight for each origin")
    failure_reason: Optional[str] = Field(description="Explanation if convergence failed")

# ── Hotel & Activity Outputs ────────────────────────────────────────────────

class HotelProposal(BaseModel):
    name: str
    price_per_night_usd: int
    total_price_usd: int
    rating: float
    description: str
    booking_link: Optional[str]
    images: List[str]

class ActivityItem(BaseModel):
    name: str
    type: str = Field(description="e.g., 'Restaurant', 'Museum', 'Event'")
    description: str
    address: str
    time_suggestion: str = Field(description="e.g., 'Day 1 Afternoon', 'Dinner'")
    link: Optional[str]
    thumbnail: Optional[str]

# ── Final Group Itinerary ──────────────────────────────────────────────────

class GroupItinerary(BaseModel):
    """The final structured JSON output sent to the frontend."""
    destination: str
    outbound_date: str
    return_date: Optional[str]
    convergence: ConvergedItinerary
    hotels: List[HotelProposal]
    activities: List[ActivityItem]
    price_intelligence: str = Field(description="Summary of price trends and booking advice")
