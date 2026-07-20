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

class AuthResponse(BaseModel):
    token: TokenResponse
    user: UserResponse
