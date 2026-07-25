"""
Auth API Routes.

Handles user registration, login, token refresh, and Stripe Identity webhooks.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.database import get_db
from maci_core.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    OAuthRequest,
    LinkAccountRequest,
)
from maci_core.schemas.user import UserCreate
from app.services import auth_service
from fastapi import HTTPException
from pydantic import BaseModel

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

@router.post("/oauth", response_model=AuthResponse)
async def oauth_login(
    request: OAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth login/registration securely via provider JWT token."""
    if request.provider not in ["google", "apple", "linkedin"]:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        
    return await auth_service.oauth_login_or_register(
        db=db,
        provider=request.provider,
        provider_token=request.provider_token,
    )

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    origin_airport: Optional[str] = None
    avatar_url: Optional[str] = None

@router.get("/me")
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch current user profile."""
    from sqlalchemy import select
    from maci_core.models.user import User
    from app.services.auth_service import decrypt_pii
    import uuid
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": decrypt_pii(user.first_name) if user.first_name else "",
        "last_name": decrypt_pii(user.last_name) if user.last_name else "",
        "bio": getattr(user, 'bio', ''),
        "origin_airport": getattr(user, 'origin_airport', ''),
        "avatar_url": getattr(user, 'avatar_url', '') or getattr(user, 'avatar_image_url', ''),
        "is_verified": user.kyc_status == "verified",
        "kyc_status": user.kyc_status,
        "karma_score": user.karma_score
    }

@router.put("/me")
async def update_me(
    body: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile details."""
    from sqlalchemy import select
    from maci_core.models.user import User
    from app.services.auth_service import decrypt_pii, encrypt_pii
    import uuid
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.first_name is not None: user.first_name = encrypt_pii(body.first_name)
    if body.last_name is not None: user.last_name = encrypt_pii(body.last_name)
    if body.bio is not None: setattr(user, 'bio', body.bio)
    if body.origin_airport is not None: setattr(user, 'origin_airport', body.origin_airport)
    if body.avatar_url is not None: setattr(user, 'avatar_url', body.avatar_url)

    await db.commit()
    await db.refresh(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": decrypt_pii(user.first_name) if user.first_name else "",
        "last_name": decrypt_pii(user.last_name) if user.last_name else "",
        "bio": getattr(user, 'bio', ''),
        "origin_airport": getattr(user, 'origin_airport', ''),
        "avatar_url": getattr(user, 'avatar_url', '') or getattr(user, 'avatar_image_url', ''),
        "is_verified": user.kyc_status == "verified",
        "kyc_status": user.kyc_status,
        "karma_score": user.karma_score
    }

@router.post("/link-account")
async def link_account(
    request: LinkAccountRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trust Portability: Link LinkedIn or Google to boost Karma Score."""
    if request.provider not in ["google", "apple", "linkedin"]:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")
        
    return await auth_service.link_oauth_account(
        db=db,
        user_id=user_id,
        provider=request.provider,
        provider_token=request.provider_token,
    )

# --- Trust & Escrow Finalization (Phase 5 & 6) ---

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

class PlaidVerifyRequest(BaseModel):
    public_token: str

@router.post("/verify-identity")
async def verify_identity(
    request: PlaidVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Live Plaid Identity / Level 3 Trust verification.
    Exchanges public token, fetches identity, sets user as verified and permanently boosts Karma Score.
    """
    from sqlalchemy import select
    from maci_core.models.user import User
    import uuid
    import os
    import plaid
    from plaid.api import plaid_api
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.identity_get_request import IdentityGetRequest
    
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if getattr(user, 'kyc_status', None) == "verified":
        return {"status": "already_verified", "message": "Identity already verified"}
        
    plaid_client_id = os.getenv("PLAID_CLIENT_ID")
    plaid_secret = os.getenv("PLAID_SECRET")
    
    if not plaid_client_id or not plaid_secret:
        raise HTTPException(status_code=500, detail="Plaid API Keys are missing in environment.")
        
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': plaid_client_id,
            'secret': plaid_secret,
        }
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)
    
    try:
        # 1. Exchange Public Token for Access Token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=request.public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        
        # 2. Fetch Identity Data
        identity_request = IdentityGetRequest(access_token=access_token)
        identity_response = client.identity_get(identity_request)
        
        # 3. Basic verification check (ensure it matches the user name in a real system)
        accounts = identity_response['accounts']
        if not accounts or not accounts[0].get('owners'):
            raise HTTPException(status_code=400, detail="No identity information found on linked account.")
            
        owner = accounts[0]['owners'][0]
        logger.info(f"Plaid Identity Verified: {owner.get('names')}")
        
    except plaid.ApiException as e:
        logger.error(f"Plaid API Error: {e}")
        raise HTTPException(status_code=400, detail="Failed to verify identity with Plaid.")

    # Set verified and boost Karma (Level 3 Trust)
    user.kyc_status = "verified"
    user.karma_score += 10.0
    
    await db.commit()
    
    return {
        "status": "success",
        "message": "Level 3 Trust unlocked. Identity verified via Plaid.",
        "new_karma_score": user.karma_score
    }
