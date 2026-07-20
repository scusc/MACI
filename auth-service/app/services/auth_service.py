"""
Auth Service — handles user registration, login, and token management.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        first_name=request.first_name,
        last_name=request.last_name,
    )
    db.add(user)
    await db.flush()  # Flush to get the ID before committing

    # Generate tokens
    tokens = _create_token_response(user.id, request.email)

    return AuthResponse(
        token=tokens,
        user=UserResponse.model_validate(user),
    )


async def login(db: AsyncSession, request: LoginRequest) -> AuthResponse:
    """
    Authenticate a user and return tokens.

    Raises InvalidCredentialsError on failure.
    """
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.password_hash):
        raise InvalidCredentialsError()

    tokens = _create_token_response(user.id, request.email)

    return AuthResponse(
        token=tokens,
        user=UserResponse.model_validate(user),
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
