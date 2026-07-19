"""
Rally Payment Service — Razorpay Gateway Integration.
Handles Indian payments (UPI, NetBanking, Cards) via Razorpay Route.
Uses Escrow / On-hold Settlements for threshold commitment.
"""

import logging
import uuid
from typing import Dict, Any

from app.config import settings
from maci_core.schemas.rally import PaymentResponse, PaymentStatus, PaymentType, PaymentGateway

logger = logging.getLogger("rally.payment.razorpay")

class MockRazorpay:
    @staticmethod
    def order_create(**kwargs) -> Dict[str, Any]:
        return {
            "id": f"order_{uuid.uuid4().hex[:14]}",
            "entity": "order",
            "amount": kwargs.get("amount"),
            "currency": kwargs.get("currency"),
            "status": "created",
        }
    
    @staticmethod
    def route_transfer(order_id: str) -> Dict[str, Any]:
        return {
            "id": f"trf_{uuid.uuid4().hex[:14]}",
            "status": "processed",
        }
    
    @staticmethod
    def refund(order_id: str) -> Dict[str, Any]:
        return {
            "id": f"rfnd_{uuid.uuid4().hex[:14]}",
            "status": "processed",
        }


async def create_order(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    amount: int,
    platform_fee: int,
    currency: str = "INR"
) -> PaymentResponse:
    """
    Create a Razorpay Order for Escrow (Route on-hold settlement).
    """
    logger.info("Creating Razorpay Order for member %s (trip %s) - %s %d", member_id, trip_id, currency, amount)

    total_amount = amount + platform_fee

    # In a real implementation:
    # 1. We create an Order
    # 2. In the webhook (payment.captured), we create a Transfer via Route
    #    with `on_hold: 1` (this is the Escrow mechanic)
    
    order = MockRazorpay.order_create(
        amount=total_amount,
        currency=currency.upper(),
        receipt=f"rcpt_{trip_id.hex[:8]}_{member_id.hex[:8]}",
        notes={
            "trip_id": str(trip_id),
            "member_id": str(member_id),
            "platform_fee": str(platform_fee)
        }
    )

    return PaymentResponse(
        id=uuid.uuid4(),  # Local DB ID
        trip_id=trip_id,
        member_id=member_id,
        amount=amount,
        platform_fee=platform_fee,
        currency=currency,
        gateway=PaymentGateway.RAZORPAY,
        status=PaymentStatus.PENDING,
        payment_type=PaymentType.DEPOSIT,
        razorpay_order_id=order["id"],
        razorpay_key_id=settings.razorpay_key_id
    )


async def release_escrow(order_id: str, transfer_id: str = None) -> bool:
    """Release funds to the organizer via Razorpay Route."""
    logger.info("Releasing Razorpay Escrow for order %s", order_id)
    # In real Route, we call /transfers/{transfer_id}/reversals OR we just lift the hold
    result = MockRazorpay.route_transfer(order_id)
    return result["status"] == "processed"


async def refund_order(order_id: str) -> bool:
    """Refund a Razorpay order that is in escrow/hold."""
    logger.info("Refunding Razorpay order %s", order_id)
    result = MockRazorpay.refund(order_id)
    return result["status"] == "processed"
