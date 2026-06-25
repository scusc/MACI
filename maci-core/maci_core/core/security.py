"""
MACI Security Utilities.

JWT token creation/verification and password hashing.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from maci_core.config import settings
from maci_core.core.exceptions import TokenExpiredError, TokenInvalidError


# ── Password Hashing ─────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT Tokens ───────────────────────────────────────────────────────

def create_access_token(org_id: uuid.UUID, email: str) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(org_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(org_id: uuid.UUID, email: str) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(org_id),
        "email": email,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict:
    """
    Verify and decode a JWT token.

    Returns the decoded payload dict with 'sub' (org_id) and 'email'.
    Raises TokenExpiredError or TokenInvalidError on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise TokenInvalidError()

    if payload.get("type") != expected_type:
        raise TokenInvalidError()

    return payload


def get_org_id_from_token(token: str) -> uuid.UUID:
    """Extract the organization ID from a verified access token."""
    payload = verify_token(token, expected_type="access")
    return uuid.UUID(payload["sub"])
