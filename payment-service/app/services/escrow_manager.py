"""
Slice Payment Service — Escrow Manager.
Orchestrates holding and releasing funds across Stripe and Razorpay for Pools.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Payment
from app.services import stripe_gateway, razorpay_gateway
from maci_core.schemas.payment import EscrowRelease, RefundResult

logger = logging.getLogger("rally.payment.escrow")


async def release_pool_escrow(db: AsyncSession, pool_id: uuid.UUID) -> EscrowRelease:
    """
    Capture all authorized payments for a pool.
    Called when the pool reaches the 'CONFIRMED' state (post Vibe Check window).
    """
    logger.info("Capturing escrow for pool %s (Confirmed State)", pool_id)

    result = await db.execute(
        select(Payment)
        .where(Payment.pool_id == pool_id)
        .where(Payment.status == "authorized")
    )
    held_payments = result.scalars().all()

    total_released = 0
    gateway_ids = []

    for payment in held_payments:
        success = False
        if payment.gateway == "stripe":
            success = await stripe_gateway.capture_payment(payment.gateway_payment_id)
        elif payment.gateway == "razorpay":
            success = await razorpay_gateway.release_escrow(payment.gateway_payment_id, payment.gateway_transfer_id)

        if success:
            payment.status = "captured"
            payment.escrow_released_at = datetime.utcnow()
            total_released += payment.amount
            gateway_ids.append(payment.gateway_payment_id)
            logger.info("Captured payment %s (%d cents)", payment.id, payment.amount)
        else:
            logger.error("Failed to capture payment %s", payment.id)

    await db.commit()

    # Trigger vendor payout via Stripe Connect Express
    from maci_core.models.pool import Pool
    from maci_core.models.user import User
    
    vendor_stmt = (
        select(User.stripe_connect_id)
        .join(Pool, Pool.host_id == User.id)
        .where(Pool.id == pool_id)
    )
    vendor_stripe_account_id = (await db.execute(vendor_stmt)).scalar()
    
    if not vendor_stripe_account_id:
        logger.error(f"Vendor for pool {pool_id} does not have a connected Stripe account. Payout aborted.")
        payout_success = False
    else:
        payout_success = await execute_vendor_payout(db, pool_id, vendor_stripe_account_id)

    return EscrowRelease(
        pool_id=pool_id,
        amount_released=total_released,
        status="success" if (held_payments and payout_success) else "partial_failure"
    )


async def refund_pool_escrow(db: AsyncSession, pool_id: uuid.UUID) -> RefundResult:
    """
    Refund/Cancel all authorized payments for a pool (funding failed/expired).
    """
    logger.info("Canceling authorizations for pool %s", pool_id)

    result = await db.execute(
        select(Payment)
        .where(Payment.pool_id == pool_id)
        .where(Payment.status == "authorized")
    )
    held_payments = result.scalars().all()

    total_refunded = 0
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
            logger.info("Canceled payment %s (%d cents)", payment.id, payment.amount)
        else:
            payment.status = "failed"
            failed_refunds.append(str(payment.id))
            logger.error("Failed to cancel payment %s", payment.id)

    await db.commit()

    return RefundResult(
        pool_id=pool_id,
        amount_refunded=total_refunded,
        status="success" if not failed_refunds else "partial_failure"
    )

async def cancel_single_authorization(db: AsyncSession, pool_id: uuid.UUID, member_id: uuid.UUID) -> bool:
    """
    Cancel a single user's pre-authorization.
    Called when a user 'Withdraws' during the Vibe Check Window.
    """
    logger.info(f"Canceling authorization for member {member_id} in pool {pool_id}")
    
    result = await db.execute(
        select(Payment)
        .where(Payment.pool_id == pool_id)
        .where(Payment.member_id == member_id)
        .where(Payment.status == "authorized")
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        logger.warning(f"No authorized payment found for member {member_id}")
        return False
        
    success = False
    if payment.gateway == "stripe":
        success = await stripe_gateway.refund_payment(payment.gateway_payment_id)
    elif payment.gateway == "razorpay":
        success = await razorpay_gateway.refund_order(payment.gateway_payment_id)
        
    if success:
        payment.status = "refunded"
        payment.refunded_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Successfully canceled authorization for payment {payment.id}")
        return True
        
    logger.error(f"Failed to cancel authorization for payment {payment.id}")
    return False

import stripe
from maci_core.config import settings

async def execute_vendor_payout(db: AsyncSession, pool_id: uuid.UUID, vendor_stripe_account_id: str) -> bool:
    """
    Transfers the captured Escrow funds to the Vendor's connected Stripe account.
    This completes the final leg of the Escrow journey.
    """
    logger.info(f"Executing vendor payout for pool {pool_id} to {vendor_stripe_account_id}")
    
    # Calculate the total captured amount for this pool
    result = await db.execute(
        select(Payment)
        .where(Payment.pool_id == pool_id)
        .where(Payment.status == "captured")
    )
    captured_payments = result.scalars().all()
    
    if not captured_payments:
        logger.warning(f"No captured payments found for pool {pool_id} to payout.")
        return False
        
    total_amount_cents = sum(p.amount for p in captured_payments)
    
    # --- BUSINESS MODEL: 5% Platform Fee ---
    PLATFORM_FEE_PERCENTAGE = 0.05
    platform_fee_cents = int(total_amount_cents * PLATFORM_FEE_PERCENTAGE)
    payout_amount_cents = total_amount_cents - platform_fee_cents
    
    logger.info(f"Pool {pool_id} Revenue: {platform_fee_cents} cents. Paying Vendor: {payout_amount_cents} cents.")
    
    # Execute the Stripe Transfer to the connected account
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        transfer = stripe.Transfer.create(
            amount=payout_amount_cents,
            currency="usd",
            destination=vendor_stripe_account_id,
            description=f"Slice Escrow Payout for Pool {pool_id}"
        )
        logger.info(f"Successfully transferred {payout_amount_cents} cents to {vendor_stripe_account_id}. Transfer ID: {transfer.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to execute Stripe Transfer: {e}")
        return False
