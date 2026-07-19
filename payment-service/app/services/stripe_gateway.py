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

# Mock Stripe SDK (replace with actual stripe-python in prod)
class MockStripe:
    @staticmethod
    def PaymentIntent_create(**kwargs) -> Dict[str, Any]:
        return {
            "id": f"pi_{uuid.uuid4().hex[:14]}",
            "client_secret": f"pi_{uuid.uuid4().hex[:14]}_secret_{uuid.uuid4().hex[:14]}",
            "status": "requires_payment_method",
            "amount": kwargs.get("amount"),
            "currency": kwargs.get("currency"),
            "capture_method": kwargs.get("capture_method"),
        }
    
    @staticmethod
    def PaymentIntent_capture(intent_id: str) -> Dict[str, Any]:
        return {
            "id": intent_id,
            "status": "succeeded",
        }
    
    @staticmethod
    def PaymentIntent_cancel(intent_id: str) -> Dict[str, Any]:
        return {
            "id": intent_id,
            "status": "canceled",
        }


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

    intent = MockStripe.PaymentIntent_create(
        amount=total_amount,
        currency=currency.lower(),
        capture_method="manual",  # IMPORTANT: This creates the Escrow behavior
        metadata={
            "trip_id": str(trip_id),
            "member_id": str(member_id),
            "platform_fee": str(platform_fee)
        }
    )

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
        stripe_client_secret=intent["client_secret"]
    )


async def capture_payment(payment_intent_id: str) -> bool:
    """Capture a previously authorized PaymentIntent (Release Escrow)."""
    logger.info("Capturing Stripe PaymentIntent %s", payment_intent_id)
    result = MockStripe.PaymentIntent_capture(payment_intent_id)
    return result["status"] == "succeeded"


async def refund_payment(payment_intent_id: str) -> bool:
    """Cancel an uncaptured PaymentIntent (Refund Escrow)."""
    logger.info("Canceling Stripe PaymentIntent %s", payment_intent_id)
    result = MockStripe.PaymentIntent_cancel(payment_intent_id)
    return result["status"] == "canceled"
