"""Auth request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Register a new organization + admin user."""
    org_name: str = Field(..., min_length=2, max_length=255, examples=["Acme Corp"])
    email: EmailStr = Field(..., examples=["admin@acme.com"])
    password: str = Field(..., min_length=8, max_length=128)
    domain: str | None = Field(None, max_length=255, examples=["acme.com"])


class LoginRequest(BaseModel):
    """Login with email and password."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh an access token using a refresh token."""
    refresh_token: str


class TokenResponse(BaseModel):
    """JWT token pair returned on successful auth."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ..., description="Access token expiry in seconds."
    )


class OrgResponse(BaseModel):
    """Organization details returned in auth responses."""
    id: uuid.UUID
    name: str
    email: str
    domain: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Full auth response with tokens and org details."""
    tokens: TokenResponse
    organization: OrgResponse


# ── Rally Auth Schemas ────────────────────────────────────────────────

class RallyRegisterRequest(BaseModel):
    """Register a new user (Organizer or standard user) in Rally."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    phone: str | None = None


class RallyUserResponse(BaseModel):
    """User details returned in Rally auth."""
    id: uuid.UUID
    email: str
    display_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RallyAuthResponse(BaseModel):
    """Full auth response with tokens and user details for Rally."""
    tokens: TokenResponse
    user: RallyUserResponse
