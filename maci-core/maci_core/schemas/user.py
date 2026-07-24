"""Pydantic schemas for Users in Slice."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from typing import Optional

from maci_core.schemas.profile import PsychometricProfileResponse

class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    avatar_name: Optional[str] = None
    avatar_image_url: Optional[str] = None
    google_id: Optional[str] = None
    apple_id: Optional[str] = None
    linkedin_id: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    is_verified: bool
    kyc_status: str
    karma_score: float
    created_at: datetime
    psychometric_profile: Optional[PsychometricProfileResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
