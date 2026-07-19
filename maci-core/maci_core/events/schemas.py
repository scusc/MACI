"""
Cross-service asynchronous event schemas for Azure Service Bus.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class BaseEvent(BaseModel):
    """Base schema for all Service Bus events."""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"

class PaymentIntentAuthorizedEvent(BaseEvent):
    """Fired when an attendee successfully commits funds (authorization hold)."""
    trip_id: str
    member_id: str
    payment_intent_id: str
    amount: int
    currency: str

class TripThresholdReachedEvent(BaseEvent):
    """Fired when a trip reaches its critical mass commitment threshold."""
    trip_id: str
    trip_title: str
    organizer_id: str
    total_committed_amount: int

class MemberNudgeRequestedEvent(BaseEvent):
    """Fired when an AI nudge should be sent to a member."""
    trip_id: str
    member_id: str
    member_email: str
    member_name: str
    trip_title: str
    destination: str
    progress_pct: int
    threshold_pct: int
    member_status: str
    origin_airport: Optional[str] = None
    price_trend: str = "stable"
