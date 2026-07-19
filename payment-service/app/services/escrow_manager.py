"""
Rally Payment Service — Escrow Manager.
Orchestrates holding and releasing funds across Stripe and Razorpay.
"""

import logging
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Payment
from app.services import stripe_gateway, razorpay_gateway
from maci_core.schemas.rally import EscrowRelease, RefundResult

logger = logging.getLogger("rally.payment.escrow")


async def release_trip_escrow(db: AsyncSession, trip_id: uuid.UUID) -> EscrowRelease:
    """
    Release all held payments for a trip (threshold met).
    Captures Stripe PaymentIntents and releases Razorpay Route holds.
    """
    logger.info("Releasing escrow for trip %s", trip_id)

    result = await db.execute(
        select(Payment)
        .where(Payment.trip_id == trip_id)
        .where(Payment.status == "held")
    )
    held_payments = result.scalars().all()

    total_released = 0
    released_count = 0
    gateway_ids = []

    for payment in held_payments:
        success = False
        if payment.gateway == "stripe":
            success = await stripe_gateway.capture_payment(payment.gateway_payment_id)
        elif payment.gateway == "razorpay":
            success = await razorpay_gateway.release_escrow(payment.gateway_payment_id, payment.gateway_transfer_id)

        if success:
            payment.status = "released"
            payment.escrow_released_at = datetime.utcnow()
            total_released += payment.amount
            released_count += 1
            gateway_ids.append(payment.gateway_payment_id)
            logger.info("Released payment %s (%d cents)", payment.id, payment.amount)
        else:
            logger.error("Failed to release payment %s", payment.id)

    await db.commit()

    return EscrowRelease(
        trip_id=trip_id,
        total_released=total_released,
        payments_released=released_count,
        gateway_transfer_ids=gateway_ids
    )


async def refund_trip_escrow(db: AsyncSession, trip_id: uuid.UUID) -> RefundResult:
    """
    Refund/Cancel all held payments for a trip (trip cancelled).
    """
    logger.info("Refunding escrow for trip %s", trip_id)

    result = await db.execute(
        select(Payment)
        .where(Payment.trip_id == trip_id)
        .where(Payment.status == "held")
    )
    held_payments = result.scalars().all()

    total_refunded = 0
    refunded_count = 0
    failed_refunds = []

    for payment in held_payments:
        success = False
        if payment.gateway == "stripe":
            success = await stripe_gateway.refund_payment(payment.gateway_payment_id)
        elif payment.gateway == "razorpay":
            success = await razorpay_gateway.refund_order(payment.gateway_payment_id)

        if success:
            payment.status = "refunded"
            payment.refunded_at = datetime.utcnow()
            total_refunded += payment.amount
            refunded_count += 1
            logger.info("Refunded payment %s (%d cents)", payment.id, payment.amount)
        else:
            payment.status = "failed"
            failed_refunds.append(str(payment.id))
            logger.error("Failed to refund payment %s", payment.id)

    await db.commit()

    return RefundResult(
        trip_id=trip_id,
        total_refunded=total_refunded,
        payments_refunded=refunded_count,
        failed_refunds=failed_refunds
    )
