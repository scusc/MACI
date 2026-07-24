"""
Trust Passport Subscription Routes — $9.99/month Premium Tier in Rally.
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from maci_core.database import get_db
from maci_core.models.user import User
from maci_core.schemas.subscription import SubscriptionCheckoutRequest, SubscriptionStatusResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token

router = APIRouter(prefix="/subscription", tags=["Trust Passport Subscription"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the user's current Trust Passport subscription status ($9.99/mo).
    """
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_active = (
        user.subscription_tier == "trust_passport" and
        (user.subscription_expires_at is None or user.subscription_expires_at > datetime.now(timezone.utc))
    )

    return SubscriptionStatusResponse(
        user_id=str(user.id),
        subscription_tier=user.subscription_tier,
        is_active=is_active,
        expires_at=user.subscription_expires_at,
        checkout_url="https://checkout.stripe.com/pay/trust_passport_999"
    )


@router.post("/activate", response_model=SubscriptionStatusResponse)
async def activate_trust_passport(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Activates / upgrades user to $9.99/mo Trust Passport Subscription.
    Unlocks ZK Privacy Vault, Verified Trust Badge, and Priority Psychometric AI Matching.
    """
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.subscription_tier = "trust_passport"
    user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    user.karma_score += 5.0 # Subscription loyalty boost
    await db.commit()
    await db.refresh(user)

    return SubscriptionStatusResponse(
        user_id=str(user.id),
        subscription_tier=user.subscription_tier,
        is_active=True,
        expires_at=user.subscription_expires_at
    )
