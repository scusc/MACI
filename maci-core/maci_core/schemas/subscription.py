"""
Subscription Schemas — Pydantic models for Trust Passport $9.99/mo in Rally.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class SubscriptionCheckoutRequest(BaseModel):
    success_url: Optional[str] = "http://localhost:4200/subscription?status=success"
    cancel_url: Optional[str] = "http://localhost:4200/subscription?status=cancel"


class SubscriptionStatusResponse(BaseModel):
    user_id: str
    subscription_tier: str # 'free' or 'trust_passport'
    is_active: bool
    expires_at: Optional[datetime] = None
    checkout_url: Optional[str] = None
