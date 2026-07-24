"""
Escrow Micro-Commitments & Group Trip Escrows — Payment Service in Rally.
"""

import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging

from app.db import get_db
from app.config import settings
from maci_core.models.meetup import Meetup, MeetupMember, MeetupMemberStatus

logger = logging.getLogger("rally.payment.escrow")
router = APIRouter(prefix="/escrow", tags=["Escrow Engine"])

# Setup Stripe
stripe.api_key = settings.stripe_api_key


@router.post("/{meetup_id}/join")
async def join_meetup_escrow(
    meetup_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates an escrow hold for a local meetup (<7 days).
    Uses Stripe manual authorization hold (capture_method="manual").
    """
    stmt = select(Meetup).where(Meetup.id == uuid.UUID(meetup_id))
    meetup = (await db.execute(stmt)).scalar_one_or_none()
    
    if not meetup:
        raise HTTPException(status_code=404, detail="Meetup not found")
        
    if meetup.status != "open":
        raise HTTPException(status_code=400, detail="Meetup is not open")

    try:
        intent = stripe.PaymentIntent.create(
            amount=meetup.escrow_amount_cents,
            currency="usd",
            capture_method="manual", # 7-day auth hold for local meetup
            description=f"Escrow Hold for Local Meetup: {meetup.title}",
            metadata={"meetup_id": meetup_id, "user_id": user_id, "type": "meetup_hold"}
        )
    except Exception as e:
        logger.error(f"Stripe Escrow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    member = MeetupMember(
        meetup_id=meetup.id,
        user_id=uuid.UUID(user_id),
        stripe_payment_intent_id=intent.id,
        status=MeetupMemberStatus.pending
    )
    db.add(member)
    await db.commit()
    
    return {"client_secret": intent.client_secret, "status": "requires_payment_method"}


@router.post("/trip/{trip_id}/deposit")
async def trip_escrow_deposit(
    trip_id: str,
    user_id: str,
    amount_cents: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Direct escrow pool charge for long-term group trips (>7 days out).
    Uses capture_method="automatic" so funds are captured into escrow balance immediately 
    and held safely without expiring after 7 days.
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            capture_method="automatic", # Immediate charge into escrow balance for long trips
            description=f"Escrow Deposit for Group Trip: {trip_id}",
            metadata={"trip_id": trip_id, "user_id": user_id, "type": "trip_escrow"}
        )
        return {"client_secret": intent.client_secret, "payment_intent_id": intent.id, "status": "escrow_charged"}
    except Exception as e:
        logger.error(f"Stripe Trip Escrow Deposit Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/release")
async def release_escrow(
    payment_intent_id: str
):
    """
    Cancels the authorization hold (User Checked In to local meetup).
    """
    try:
        stripe.PaymentIntent.cancel(payment_intent_id)
        return {"status": "cancelled", "message": "Hold released successfully."}
    except Exception as e:
        logger.error(f"Stripe Release Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture")
async def capture_escrow(
    payment_intent_id: str
):
    """
    Captures the authorization hold (User Flaked on local meetup).
    """
    try:
        stripe.PaymentIntent.capture(payment_intent_id)
        return {"status": "captured", "message": "Funds captured successfully (Penalty)."}
    except Exception as e:
        logger.error(f"Stripe Capture Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refund-trip")
async def refund_trip_escrow(
    payment_intent_id: str
):
    """
    Refunds a long-term trip escrow deposit (e.g., if Vibe Check fails by >50% vote).
    """
    try:
        refund = stripe.Refund.create(payment_intent=payment_intent_id)
        return {"status": "refunded", "refund_id": refund.id, "message": "Trip deposit refunded."}
    except Exception as e:
        logger.error(f"Stripe Refund Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
