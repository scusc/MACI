"""
Auth API Routes.

Handles user registration, login, token refresh, and Stripe Identity webhooks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.database import get_db
from maci_core.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from maci_core.schemas.user import UserCreate
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new B2C user."""
    return await auth_service.register(db, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password. Returns JWT token pair and User data."""
    return await auth_service.login(db, request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token using a valid refresh token."""
    return await auth_service.refresh_tokens(db, request.refresh_token)

# --- Trust & Escrow Finalization (Phase 5 & 6) ---

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token
from fastapi import HTTPException

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/kyc/start")
async def start_kyc(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generates a Stripe Identity Verification link for a traveler."""
    from sqlalchemy import select
    from maci_core.models.user import User
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    url = await auth_service.create_kyc_session(db, user)
    return {"verification_url": url}

@router.post("/host/onboard")
async def onboard_host(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generates a Stripe Connect Express link for a host."""
    from sqlalchemy import select
    from maci_core.models.user import User
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    url = await auth_service.create_vendor_onboarding(db, user)
    return {"onboarding_url": url}

import stripe
from maci_core.config import settings
from fastapi import Request

@router.post("/webhooks/stripe")
async def auth_stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhooks for Identity (KYC) and Connect."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid signature or payload")
        
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    if event_type == "identity.verification_session.verified":
        user_id = data.get("metadata", {}).get("user_id")
        if user_id:
            from sqlalchemy import select
            from maci_core.models.user import User
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.kyc_status = "verified"
                await db.commit()
                
    return {"status": "success"}
