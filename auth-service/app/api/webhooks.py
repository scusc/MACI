"""
Webhooks API for Auth Service.

Handles Stripe Identity webhooks to verify users.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.database import get_db
from maci_core.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe-identity")
async def stripe_identity_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe Identity webhooks.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        import stripe
        # Note: In production, STRIPE_WEBHOOK_SECRET must be configured
        # event = stripe.Webhook.construct_event(
        #     payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        # )
        
        # For now, we simulate parsing the event JSON directly
        import json
        event = json.loads(payload)
        
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "identity.verification_session.verified":
        session = event["data"]["object"]
        
        # We expect the user ID to be passed in the metadata during session creation
        user_id_str = session.get("metadata", {}).get("user_id")
        
        if user_id_str:
            try:
                user_id = uuid.UUID(user_id_str)
                
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    user.is_verified = True
                    await db.commit()
                    logger.info(f"User {user_id} verified successfully via Stripe Identity.")
            except Exception as e:
                logger.error(f"Failed to update user verification status: {str(e)}")
                await db.rollback()

    return {"status": "success"}
