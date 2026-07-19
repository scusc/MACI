"""
Rally Payment Service — Webhook handlers for Stripe and Razorpay.
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from sqlalchemy import select

from app.db import get_db
from app.models.models import Payment

logger = logging.getLogger("rally.payment.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhooks."""
    payload = await request.json()
    # In production, verify stripe signature here
    
    event_type = payload.get("type")
    data = payload.get("data", {}).get("object", {})
    
    if event_type == "payment_intent.amount_capturable_updated":
        # This means the manual capture payment was authorized and is now held in escrow
        intent_id = data.get("id")
        logger.info("Stripe PaymentIntent %s authorized (held in escrow)", intent_id)
        
        result = await db.execute(select(Payment).where(Payment.gateway_payment_id == intent_id))
        payment = result.scalar_one_or_none()
        
        if payment and payment.status == "pending":
            payment.status = "held"
            await db.commit()
            
            # TODO: Call Group Service to mark member as Paid and check threshold
            
    return {"status": "success"}

@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay webhooks."""
    payload = await request.json()
    # In production, verify razorpay signature here
    
    event_type = payload.get("event")
    data = payload.get("payload", {}).get("payment", {}).get("entity", {})
    
    if event_type == "payment.captured":
        order_id = data.get("order_id")
        logger.info("Razorpay Order %s captured (held in escrow via Route)", order_id)
        
        result = await db.execute(select(Payment).where(Payment.gateway_payment_id == order_id))
        payment = result.scalar_one_or_none()
        
        if payment and payment.status == "pending":
            payment.status = "held"
            # In real Route, we would capture the transfer_id here
            payment.gateway_transfer_id = "trf_mock"
            await db.commit()
            
            # TODO: Call Group Service to mark member as Paid and check threshold

    return {"status": "success"}
