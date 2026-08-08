"""
Rally Payment Service — Payment API routes for Slice (Micro-pooling).
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.models import Payment
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember
from app.services import stripe_gateway, razorpay_gateway, escrow_manager
from app.services.split_calculator import calculate_platform_fee

from maci_core.schemas.payment import (
    PaymentCreate, PaymentResponse, EscrowRelease, RefundResult,
    PaymentGateway, PaymentType
)

logger = logging.getLogger("rally.payment.routes")

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/onboard")
async def onboard_organizer(user_id: uuid.UUID):
    """
    Generate a Stripe Connect onboarding link for a host.
    """
    try:
        import stripe
        # Create an account
        account = stripe.Account.create(type="express")
        
        # Create an account link
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url="https://slice.app/reauth",
            return_url="https://slice.app/return",
            type="account_onboarding",
        )
        return {"url": account_link.url, "account_id": account.id}
    except Exception as e:
        logger.error("Stripe onboarding error: %s", str(e))
        raise HTTPException(status_code=500, detail="Onboarding failed")


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new pre-authorization payment for a Pool Member.
    We do NOT capture funds here. We authorize the card to hold the slice.
    """
    platform_fee = calculate_platform_fee(body.amount)
    
    payment = Payment(
        pool_id=body.pool_id,
        member_id=body.member_id,
        amount=body.amount,
        platform_fee=platform_fee,
        currency=body.currency,
        gateway=body.gateway.value,
        payment_type=body.payment_type.value,
        status="authorized" # Held in escrow
    )
    db.add(payment)
    await db.flush()

    try:
        if body.gateway == PaymentGateway.STRIPE:
            # We must use capture_method='manual' to hold the funds
            response = await stripe_gateway.create_payment_intent(
                trip_id=body.pool_id, # Using pool_id internally
                member_id=body.member_id,
                amount=int(body.amount),
                platform_fee=platform_fee,
                currency=body.currency
            )
            payment.gateway_payment_id = response.stripe_client_secret.split("_secret_")[0]
        
        elif body.gateway == PaymentGateway.RAZORPAY:
            # Razorpay auth and capture is slightly different, but concept holds
            response = await razorpay_gateway.create_order(
                trip_id=body.pool_id,
                member_id=body.member_id,
                amount=body.amount,
                platform_fee=platform_fee,
                currency=body.currency
            )
            payment.gateway_payment_id = response.razorpay_order_id
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported gateway")

        await db.commit()
        
        return PaymentResponse(
            id=payment.id,
            gateway_payment_id=payment.gateway_payment_id
        )

    except Exception as e:
        await db.rollback()
        logger.error("Failed to create pre-authorization: %s", str(e))
        raise HTTPException(status_code=500, detail="Payment gateway error")


@router.post("/{pool_id}/release-escrow", response_model=EscrowRelease)
async def release_pool_escrow(pool_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Capture all authorized funds for a pool (threshold met)."""
    return await escrow_manager.release_trip_escrow(db, pool_id)


@router.post("/{pool_id}/refund-all", response_model=RefundResult)
async def refund_pool_escrow(pool_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel all authorizations for a pool (funding failed)."""
    return await escrow_manager.refund_trip_escrow(db, pool_id)
