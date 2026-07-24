"""Pydantic schemas for Authentication in Slice."""

from pydantic import BaseModel
from maci_core.schemas.user import UserResponse

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class RefreshRequest(BaseModel):
    refresh_token: str

class OAuthRequest(BaseModel):
    provider: str  # e.g., 'google', 'apple', 'linkedin'
    provider_token: str # Replaces raw data. Token to be verified against provider's public JWKS.

class LinkAccountRequest(BaseModel):
    provider: str
    provider_token: str

class AuthResponse(BaseModel):
    token: TokenResponse
    user: UserResponse
