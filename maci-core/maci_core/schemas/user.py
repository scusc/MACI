"""Pydantic schemas for Users in Slice."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    email: str
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    is_verified: bool
    karma_score: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
