"""
Rally Payment Service — Stripe Gateway Integration.
Handles US/International cards via Stripe Connect.
Uses `capture_method="manual"` to implement Escrow.
"""

import logging
import uuid
from typing import Dict, Any

from app.config import settings
from maci_core.schemas.rally import PaymentResponse, PaymentStatus, PaymentType, PaymentGateway

logger = logging.getLogger("rally.payment.stripe")

import stripe

stripe.api_key = settings.stripe_api_key


async def create_payment_intent(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    amount: int,
    platform_fee: int,
    currency: str = "USD"
) -> PaymentResponse:
    """
    Create a Stripe PaymentIntent with manual capture for Escrow.
    """
    logger.info("Creating Stripe PaymentIntent for member %s (trip %s) - %s %d", member_id, trip_id, currency, amount)

    # In a real implementation, we would pass `transfer_data={"destination": organizer_stripe_account}`
    # and `application_fee_amount=platform_fee` for Stripe Connect.
    
    total_amount = amount + platform_fee

    try:
        intent = stripe.PaymentIntent.create(
            amount=total_amount,
            currency=currency.lower(),
            capture_method="manual",  # IMPORTANT: Escrow behavior
            metadata={
                "trip_id": str(trip_id),
                "member_id": str(member_id),
                "platform_fee": str(platform_fee)
            }
            # For real Connect:
            # application_fee_amount=platform_fee,
            # transfer_data={"destination": "acct_12345"}
        )
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        raise

    return PaymentResponse(
        id=uuid.uuid4(),  # Local DB ID (to be created by routes)
        trip_id=trip_id,
        member_id=member_id,
        amount=amount,
        platform_fee=platform_fee,
        currency=currency,
        gateway=PaymentGateway.STRIPE,
        status=PaymentStatus.PENDING,
        payment_type=PaymentType.DEPOSIT,
        stripe_client_secret=intent.client_secret
    )


async def capture_payment(payment_intent_id: str) -> bool:
    """Capture a previously authorized PaymentIntent (Release Escrow)."""
    logger.info("Capturing Stripe PaymentIntent %s", payment_intent_id)
    try:
        intent = stripe.PaymentIntent.capture(payment_intent_id)
        return intent.status == "succeeded"
    except Exception as e:
        logger.error(f"Failed to capture PaymentIntent {payment_intent_id}: {e}")
        return False


async def refund_payment(payment_intent_id: str) -> bool:
    """Cancel an uncaptured PaymentIntent (Refund Escrow)."""
    logger.info("Canceling Stripe PaymentIntent %s", payment_intent_id)
    try:
        intent = stripe.PaymentIntent.cancel(payment_intent_id)
        return intent.status == "canceled"
    except Exception as e:
        logger.error(f"Failed to cancel PaymentIntent {payment_intent_id}: {e}")
        return False
