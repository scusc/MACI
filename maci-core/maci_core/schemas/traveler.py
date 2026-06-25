"""Traveler request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TimeWindow(BaseModel):
    """A UTC time window when the traveler CANNOT travel."""
    start: datetime = Field(..., description="Window start (UTC ISO8601)")
    end: datetime = Field(..., description="Window end (UTC ISO8601)")


class TravelerSubmitRequest(BaseModel):
    """Submit traveler constraints via the intake link."""
    name: str = Field(..., min_length=2, max_length=255, examples=["Sai Chand"])
    email: EmailStr = Field(..., examples=["sai@acme.com"])
    origin_city: str = Field(
        ..., min_length=2, max_length=255,
        examples=["London"],
    )
    origin_iata: str = Field(
        ..., min_length=3, max_length=10,
        examples=["LHR"],
    )
    hard_budget_cents: int | None = Field(
        None, ge=0,
        description="Maximum budget per person in cents. None = no budget cap.",
        examples=[80000],
    )
    blocked_windows_utc: list[TimeWindow] = Field(
        default_factory=list,
        description="UTC time windows when traveler cannot travel.",
    )
    soft_preferences: dict | None = Field(
        default_factory=dict,
        description="Unstructured preferences fed to the AI delegate.",
        examples=[{
            "seat_preference": "window",
            "avoid_redeye": True,
            "preferred_airlines": ["British Airways", "Emirates"],
            "notes": "Need wheelchair assistance at airport",
        }],
    )


class TravelerResponse(BaseModel):
    """Traveler details returned in API responses."""
    id: uuid.UUID
    trip_id: uuid.UUID
    cluster_id: uuid.UUID | None
    name: str
    email: str
    origin_city: str | None
    origin_iata: str | None
    hard_budget_cents: int | None
    confirmation_status: str
    constraints_submitted_at: datetime | None
    created_at: datetime

    # NOTE: blocked_windows_utc and soft_preferences are NEVER
    # exposed in public responses. This enforces opaque execution.

    model_config = {"from_attributes": True}


class TravelerListResponse(BaseModel):
    """List of travelers for a trip (organizer view)."""
    travelers: list[TravelerResponse]
    total: int
    submitted_count: int
    pending_count: int
