"""
Rally Payment Service — Payment API routes.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import Payment
from app.services import stripe_gateway, razorpay_gateway, escrow_manager
from app.services.split_calculator import calculate_platform_fee

from maci_core.schemas.rally import (
    PaymentCreate, PaymentResponse, EscrowRelease, RefundResult,
    PaymentGateway, PaymentStatus
)

logger = logging.getLogger("rally.payment.routes")

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new payment for a trip member.
    Generates a Stripe PaymentIntent or Razorpay Order.
    """
    platform_fee = calculate_platform_fee(body.amount)
    
    payment = Payment(
        trip_id=body.trip_id,
        member_id=body.member_id,
        amount=body.amount,
        platform_fee=platform_fee,
        currency=body.currency,
        gateway=body.gateway.value,
        payment_type=body.payment_type.value,
        status="pending"
    )
    db.add(payment)
    await db.flush()

    try:
        if body.gateway == PaymentGateway.STRIPE:
            response = await stripe_gateway.create_payment_intent(
                trip_id=body.trip_id,
                member_id=body.member_id,
                amount=body.amount,
                platform_fee=platform_fee,
                currency=body.currency
            )
            payment.gateway_payment_id = response.stripe_client_secret.split("_secret_")[0]
        
        elif body.gateway == PaymentGateway.RAZORPAY:
            response = await razorpay_gateway.create_order(
                trip_id=body.trip_id,
                member_id=body.member_id,
                amount=body.amount,
                platform_fee=platform_fee,
                currency=body.currency
            )
            payment.gateway_payment_id = response.razorpay_order_id
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported gateway")

        await db.commit()
        
        # Override the local mock ID with the DB ID
        response.id = payment.id
        return response

    except Exception as e:
        await db.rollback()
        logger.error("Failed to create payment: %s", str(e))
        raise HTTPException(status_code=500, detail="Payment gateway error")


@router.post("/{trip_id}/release-escrow", response_model=EscrowRelease)
async def release_trip_escrow(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Release all held funds for a trip (threshold met)."""
    return await escrow_manager.release_trip_escrow(db, trip_id)


@router.post("/{trip_id}/refund-all", response_model=RefundResult)
async def refund_trip_escrow(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Refund all held funds for a trip (trip cancelled)."""
    return await escrow_manager.refund_trip_escrow(db, trip_id)
