"""Trip request/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class TripCreateRequest(BaseModel):
    """Create a new trip."""
    title: str = Field(
        ..., min_length=3, max_length=500,
        examples=["London Engineering Offsite Q3"],
    )
    description: str | None = Field(None, max_length=2000)
    destination_city: str = Field(
        ..., min_length=2, max_length=255,
        examples=["Bengaluru"],
    )
    destination_iata: str = Field(
        ..., min_length=3, max_length=10,
        examples=["BLR"],
    )
    arrival_date: date = Field(..., examples=["2025-09-15"])
    return_date: date | None = Field(None, examples=["2025-09-20"])
    max_arrival_spread_minutes: int = Field(
        default=120,
        ge=30, le=720,
        description="Maximum allowed time spread between first and last arrival (Δt_max).",
    )
    friction_weight_cents: int = Field(
        default=2500,
        ge=0, le=10000,
        description="Layover friction penalty in cents per hour ($25/hr = 2500).",
    )
    max_travelers: int | None = Field(
        None, ge=2, le=100,
        description="Maximum number of travelers. None = unlimited.",
    )
    intake_deadline: datetime | None = Field(
        None,
        description="UTC deadline for travelers to submit constraints.",
    )


class TripUpdateRequest(BaseModel):
    """Update an existing trip (only allowed in DRAFT state)."""
    title: str | None = Field(None, min_length=3, max_length=500)
    description: str | None = None
    destination_city: str | None = Field(None, min_length=2, max_length=255)
    destination_iata: str | None = Field(None, min_length=3, max_length=10)
    arrival_date: date | None = None
    return_date: date | None = None
    max_arrival_spread_minutes: int | None = Field(None, ge=30, le=720)
    friction_weight_cents: int | None = Field(None, ge=0, le=10000)
    max_travelers: int | None = Field(None, ge=2, le=100)
    intake_deadline: datetime | None = None


class TripResponse(BaseModel):
    """Trip details returned in API responses."""
    id: uuid.UUID
    org_id: uuid.UUID
    title: str
    description: str | None
    destination_city: str
    destination_iata: str
    arrival_date: date
    return_date: date | None
    max_arrival_spread_minutes: int
    friction_weight_cents: int
    status: str
    intake_token: str
    intake_deadline: datetime | None
    max_travelers: int | None
    traveler_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripListResponse(BaseModel):
    """Paginated trip list."""
    trips: list[TripResponse]
    total: int
