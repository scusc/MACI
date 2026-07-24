"""
Rally Payment Service — Razorpay Gateway Integration.
Handles Indian payments (UPI, NetBanking, Cards) via Razorpay Route.
Uses Escrow / On-hold Settlements for threshold commitment.
"""

import logging
import uuid
import asyncio
from typing import Dict, Any

from app.config import settings
from maci_core.schemas.rally import PaymentResponse, PaymentStatus, PaymentType, PaymentGateway
import razorpay

logger = logging.getLogger("rally.payment.razorpay")

# Initialize real Razorpay client
client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

async def create_order(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    amount: int,
    platform_fee: int,
    currency: str = "INR"
) -> PaymentResponse:
    """
    Create a Razorpay Order for Escrow.
    """
    logger.info("Creating LIVE Razorpay Order for member %s (trip %s) - %s %d", member_id, trip_id, currency, amount)

    total_amount = amount + platform_fee

    # Create real order via SDK in a thread since it is synchronous
    def _create():
        return client.order.create({
            "amount": total_amount,
            "currency": currency.upper(),
            "receipt": f"rcpt_{trip_id.hex[:8]}_{member_id.hex[:8]}",
            "notes": {
                "trip_id": str(trip_id),
                "member_id": str(member_id),
                "platform_fee": str(platform_fee)
            }
        })
        
    order = await asyncio.to_thread(_create)

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
    logger.info("Releasing LIVE Razorpay Escrow for order %s", order_id)
    if not transfer_id:
        logger.error("Missing transfer_id for route release on order %s", order_id)
        return False
        
    def _release():
        # In Route, if a transfer was made with on_hold: 1, 
        # we lift the hold to settle it to the vendor's linked account.
        return client.transfer.edit(transfer_id, {"on_hold": 0})
        
    try:
        await asyncio.to_thread(_release)
        return True
    except Exception as e:
        logger.error("Failed to release razorpay route escrow: %s", e)
        return False


async def refund_order(order_id: str) -> bool:
    """Refund a Razorpay order that is in escrow/hold."""
    logger.info("Refunding LIVE Razorpay order %s", order_id)
    def _refund():
        # Refund the specific order
        # First we need the payment ID associated with the order.
        # Fetching payments for order:
        payments = client.order.payments(order_id)
        if payments and payments.get('items'):
            payment_id = payments['items'][0]['id']
            return client.payment.refund(payment_id, {"amount": payments['items'][0]['amount']})
        raise ValueError("No payments found for order")
        
    try:
        await asyncio.to_thread(_refund)
        return True
    except Exception as e:
        logger.error("Failed to refund razorpay order: %s", e)
        return False
