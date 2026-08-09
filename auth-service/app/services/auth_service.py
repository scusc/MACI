"""
Auth Service — handles user registration, login, and token management.
Real OAuth verification via Google JWKS. Zero mock data.
"""

import os
import uuid

import httpx
import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

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


# ── Google JWKS Cache ────────────────────────────────────────────────
_google_jwks_cache: dict | None = None


async def _get_google_jwks() -> dict:
    """Fetch Google's public JWKS keys for ID token verification."""
    global _google_jwks_cache
    if _google_jwks_cache is not None:
        return _google_jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://www.googleapis.com/oauth2/v3/certs")
        resp.raise_for_status()
        _google_jwks_cache = resp.json()
        return _google_jwks_cache


async def register(db: AsyncSession, request: UserCreate) -> AuthResponse:
    """
    Register a new user.
    Raises DuplicateEmailError if email already exists.
    """
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise DuplicateEmailError()

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=encrypt_pii(request.first_name),
        last_name=encrypt_pii(request.last_name),
        avatar_name=generate_shielded_avatar(),
        avatar_image_url=generate_avatar_image_url(request.email),
    )
    db.add(user)
    await db.flush()

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

    user_resp = UserResponse.model_validate(user)
    user_resp.first_name = decrypt_pii(user_resp.first_name)
    user_resp.last_name = decrypt_pii(user_resp.last_name)

    return AuthResponse(
        token=tokens,
        user=user_resp,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Verify a refresh token and issue new token pair."""
    payload = verify_token(refresh_token, expected_type="refresh")
    user_id = uuid.UUID(payload["sub"])
    email = payload["email"]

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


# ── Real Google OAuth Token Verification ─────────────────────────────

async def verify_google_token(id_token: str) -> dict:
    """
    Verify a Google ID token against Google's JWKS public keys.
    Returns the decoded payload with email, name, and Google sub ID.
    Raises InvalidCredentialsError if verification fails.
    """
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        raise InvalidCredentialsError("Google OAuth is not configured on this server.")

    try:
        jwks = await _get_google_jwks()

        # Decode the header to find the key ID
        header = pyjwt.get_unverified_header(id_token)
        kid = header.get("kid")

        # Find the matching public key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

        if rsa_key is None:
            # Refresh JWKS cache and retry (keys rotate)
            global _google_jwks_cache
            _google_jwks_cache = None
            jwks = await _get_google_jwks()
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

        if rsa_key is None:
            raise InvalidCredentialsError("Unable to verify Google token: signing key not found.")

        # Verify and decode the token
        payload = pyjwt.decode(
            id_token,
            rsa_key,
            algorithms=["RS256"],
            audience=google_client_id,
            issuer=["https://accounts.google.com", "accounts.google.com"],
        )

        # Ensure email is verified by Google
        if not payload.get("email_verified", False):
            raise InvalidCredentialsError("Google account email is not verified.")

        return {
            "oauth_id": payload["sub"],
            "email": payload["email"],
            "first_name": payload.get("given_name", ""),
            "last_name": payload.get("family_name", ""),
            "picture": payload.get("picture", ""),
        }
    except pyjwt.ExpiredSignatureError:
        raise InvalidCredentialsError("Google token has expired. Please sign in again.")
    except pyjwt.InvalidTokenError as e:
        raise InvalidCredentialsError(f"Invalid Google token: {str(e)}")
    except Exception as e:
        raise InvalidCredentialsError(f"Google OAuth verification failed: {str(e)}")


async def verify_oauth_token(provider: str, token: str) -> dict:
    """
    Verify an OAuth provider token. Routes to the correct provider.
    No mock data — real verification only.
    """
    if provider == "google":
        return await verify_google_token(token)
    elif provider == "apple":
        raise InvalidCredentialsError("Apple Sign-In is not yet configured. Coming soon.")
    else:
        raise InvalidCredentialsError(f"Unsupported OAuth provider: {provider}")


async def oauth_login_or_register(
    db: AsyncSession, provider: str, provider_token: str
) -> AuthResponse:
    """Handle OAuth flow by verifying the real provider token."""
    payload = await verify_oauth_token(provider, provider_token)
    oauth_id = payload["oauth_id"]
    email = payload["email"]

    provider_id_field = f"{provider}_id"

    stmt = select(User).where(
        (User.email == email) | (getattr(User, provider_id_field, None) == oauth_id)
    ).options(selectinload(User.psychometric_profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Register new user from verified OAuth
        user = User(
            email=email,
            password_hash=hash_password(str(uuid.uuid4())),
            first_name=encrypt_pii(payload["first_name"]),
            last_name=encrypt_pii(payload["last_name"]),
            avatar_name=generate_shielded_avatar(),
            avatar_image_url=payload.get("picture") or generate_avatar_image_url(email),
            google_id=oauth_id if provider == "google" else None,
            apple_id=oauth_id if provider == "apple" else None,
            linkedin_id=oauth_id if provider == "linkedin" else None,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user.psychometric_profile = None
    else:
        # Update existing user's OAuth ID if missing
        if not getattr(user, provider_id_field, None):
            setattr(user, provider_id_field, oauth_id)

    await db.flush()

    tokens = _create_token_response(user.id, user.email)

    if not hasattr(user, 'psychometric_profile') or isinstance(user.psychometric_profile, InstrumentedAttribute):
        user.psychometric_profile = getattr(user, 'psychometric_profile', None)

    user_resp = UserResponse.model_validate(user)
    user_resp.first_name = decrypt_pii(user_resp.first_name)
    user_resp.last_name = decrypt_pii(user_resp.last_name)

    return AuthResponse(
        token=tokens,
        user=user_resp,
    )

async def link_oauth_account(db: AsyncSession, user_id: str, provider: str, provider_token: str) -> dict:
    """Links an external professional/social graph to an existing user."""
    payload = await verify_oauth_token(provider, provider_token)
    oauth_id = payload["oauth_id"]

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        setattr(user, f"{provider}_id", oauth_id)
        user.karma_score += 0.5
        await db.commit()
        return {"status": "success", "linked_provider": provider}
    return {"status": "error", "message": "User not found"}

import stripe

async def create_kyc_session(db: AsyncSession, user: User) -> str:
    """Creates a Stripe Identity session for KYC verification."""
    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.Identity.VerificationSession.create(
        type="document",
        metadata={"user_id": str(user.id)},
        return_url="http://localhost:4200/kyc-success",
    )

    user.kyc_status = "pending"
    await db.commit()

    return session.url

async def create_vendor_onboarding(db: AsyncSession, user: User) -> str:
    """Creates a Stripe Connect Express account for a vendor/host."""
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
