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
from maci_core.models.organization import Organization
from maci_core.schemas.auth import (
    AuthResponse,
    LoginRequest,
    OrgResponse,
    RegisterRequest,
    TokenResponse,
)


async def register(db: AsyncSession, request: RegisterRequest) -> AuthResponse:
    """
    Register a new organization with an admin user.

    Raises DuplicateEmailError if email already exists.
    """
    # Check for existing email
    stmt = select(Organization).where(Organization.admin_email == request.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise DuplicateEmailError()

    # Create organization
    org = Organization(
        name=request.org_name,
        admin_email=request.email,
        admin_password_hash=hash_password(request.password),
        domain=request.domain,
    )
    db.add(org)
    await db.flush()  # Flush to get the ID before committing

    # Generate tokens
    tokens = _create_token_response(org.id, request.email)

    return AuthResponse(
        tokens=tokens,
        organization=OrgResponse(
            id=org.id,
            name=org.name,
            email=org.admin_email,
            domain=org.domain,
            created_at=org.created_at,
        ),
    )


async def login(db: AsyncSession, request: LoginRequest) -> AuthResponse:
    """
    Authenticate an org admin and return tokens.

    Raises InvalidCredentialsError on failure.
    """
    stmt = select(Organization).where(Organization.admin_email == request.email)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if org is None or not verify_password(request.password, org.admin_password_hash):
        raise InvalidCredentialsError()

    tokens = _create_token_response(org.id, request.email)

    return AuthResponse(
        tokens=tokens,
        organization=OrgResponse(
            id=org.id,
            name=org.name,
            email=org.admin_email,
            domain=org.domain,
            created_at=org.created_at,
        ),
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """
    Verify a refresh token and issue new token pair.
    """
    payload = verify_token(refresh_token, expected_type="refresh")
    org_id = uuid.UUID(payload["sub"])
    email = payload["email"]

    # Verify org still exists
    stmt = select(Organization).where(Organization.id == org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if org is None:
        raise InvalidCredentialsError()

    return _create_token_response(org_id, email)


def _create_token_response(org_id: uuid.UUID, email: str) -> TokenResponse:
    """Create a TokenResponse with access + refresh tokens."""
    return TokenResponse(
        access_token=create_access_token(org_id, email),
        refresh_token=create_refresh_token(org_id, email),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
