"""
Auth Service — handles user registration, login, and token management.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from maci_core.config import settings
from maci_core.core.exceptions import DuplicateEmailError, InvalidCredentialsError
from maci_core.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from maci_core.models.user import User
from maci_core.schemas.auth import (
    AuthResponse,
    LoginRequest,
    TokenResponse,
)
from maci_core.schemas.user import UserCreate, UserResponse
from maci_core.core.crypto import encrypt_pii, decrypt_pii
from app.services.avatar import generate_shielded_avatar, generate_avatar_image_url


async def register(db: AsyncSession, request: UserCreate) -> AuthResponse:
    """
    Register a new B2C user for Slice.

    Raises DuplicateEmailError if email already exists.
    """
    # Check for existing email
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise DuplicateEmailError()

    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=encrypt_pii(request.first_name),
        last_name=encrypt_pii(request.last_name),
        avatar_name=generate_shielded_avatar(),
        avatar_image_url=generate_avatar_image_url(request.email),
    )
    db.add(user)
    await db.flush()  # Flush to get the ID before committing

    # Generate tokens
    tokens = _create_token_response(user.id, request.email)
    
    # Prevent lazy-load error for newly created user
    user.psychometric_profile = None
    user_resp = UserResponse.model_validate(user)
    user_resp.first_name = decrypt_pii(user_resp.first_name)
    user_resp.last_name = decrypt_pii(user_resp.last_name)

    return AuthResponse(
        token=tokens,
        user=user_resp,
    )


async def login(db: AsyncSession, request: LoginRequest) -> AuthResponse:
    """
    Authenticate a user and return tokens.

    Raises InvalidCredentialsError on failure.
    """
    stmt = select(User).where(User.email == request.email).options(selectinload(User.psychometric_profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.password_hash):
        raise InvalidCredentialsError()

    tokens = _create_token_response(user.id, request.email)
    
    # Decrypt for the response payload
    user_resp = UserResponse.model_validate(user)
    user_resp.first_name = decrypt_pii(user_resp.first_name)
    user_resp.last_name = decrypt_pii(user_resp.last_name)

    return AuthResponse(
        token=tokens,
        user=user_resp,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """
    Verify a refresh token and issue new token pair.
    """
    payload = verify_token(refresh_token, expected_type="refresh")
    user_id = uuid.UUID(payload["sub"])
    email = payload["email"]

    # Verify user still exists
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidCredentialsError()

    return _create_token_response(user_id, email)


def _create_token_response(user_id: uuid.UUID, email: str) -> TokenResponse:
    """Create a TokenResponse with access + refresh tokens."""
    return TokenResponse(
        access_token=create_access_token(user_id, email),
        refresh_token=create_refresh_token(user_id, email),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

async def verify_oauth_token(provider: str, token: str) -> dict:
    """
    STUB: In production, this verifies the JWT against Google/Apple/LinkedIn JWKS public keys.
    Returns the decoded payload containing email, names, and the provider's unique ID.
    """
    # MOCK implementation for current phase
    return {
        "oauth_id": f"mock_{provider}_{token[:10]}",
        "email": f"user_{token[:5]}@example.com",
        "first_name": "Mock",
        "last_name": "User",
    }

async def oauth_login_or_register(
    db: AsyncSession, provider: str, provider_token: str
) -> AuthResponse:
    """
    Handle OAuth flow securely by verifying the provider token.
    """
    payload = await verify_oauth_token(provider, provider_token)
    oauth_id = payload["oauth_id"]
    email = payload["email"]
    
    stmt = select(User).where((User.email == email) | (getattr(User, f"{provider}_id") == oauth_id)).options(selectinload(User.psychometric_profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Register new user from OAuth
        user = User(
            email=email,
            password_hash=hash_password(str(uuid.uuid4())),
            first_name=encrypt_pii(payload["first_name"]),
            last_name=encrypt_pii(payload["last_name"]),
            avatar_name=generate_shielded_avatar(),
            avatar_image_url=generate_avatar_image_url(email),
        )
        setattr(user, f"{provider}_id", oauth_id)
        db.add(user)
    else:
        # Update existing user's OAuth ID if missing
        if not getattr(user, f"{provider}_id"):
            setattr(user, f"{provider}_id", oauth_id)
            
    await db.flush()

    tokens = _create_token_response(user.id, user.email)
    
    user.psychometric_profile = getattr(user, 'psychometric_profile', None)
    user_resp = UserResponse.model_validate(user)
    user_resp.first_name = decrypt_pii(user_resp.first_name)
    user_resp.last_name = decrypt_pii(user_resp.last_name)

    return AuthResponse(
        token=tokens,
        user=user_resp,
    )

async def link_oauth_account(db: AsyncSession, user_id: str, provider: str, provider_token: str) -> dict:
    """
    Trust Portability: Links an external professional/social graph to an existing user.
    """
    payload = await verify_oauth_token(provider, provider_token)
    oauth_id = payload["oauth_id"]
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        setattr(user, f"{provider}_id", oauth_id)
        # Optionally boost Karma Score here based on LinkedIn verification
        user.karma_score += 0.5 
        await db.commit()
        return {"status": "success", "linked_provider": provider}
    return {"status": "error", "message": "User not found"}

import stripe

async def create_kyc_session(db: AsyncSession, user: User) -> str:
    """
    Creates a Stripe Identity session for KYC verification.
    Returns the URL where the user should be redirected to upload their ID.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    session = stripe.Identity.VerificationSession.create(
        type="document",
        metadata={"user_id": str(user.id)},
        return_url="http://localhost:4200/kyc-success",
    )
    
    # Update user status to pending
    user.kyc_status = "pending"
    await db.commit()
    
    return session.url

async def create_vendor_onboarding(db: AsyncSession, user: User) -> str:
    """
    Creates a Stripe Connect Express account for a vendor/host and returns the onboarding URL.
    This allows us to transfer Escrow funds directly to their bank account.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    if not user.stripe_connect_id:
        account = stripe.Account.create(
            type="express",
            email=user.email,
            capabilities={
                "transfers": {"requested": True},
            },
            metadata={"user_id": str(user.id)}
        )
        user.stripe_connect_id = account.id
        await db.commit()
        
    account_link = stripe.AccountLink.create(
        account=user.stripe_connect_id,
        refresh_url="http://localhost:4200/host-onboard-refresh",
        return_url="http://localhost:4200/host-dashboard",
        type="account_onboarding",
    )
    
    return account_link.url
