from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class MeetupCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    latitude: float
    longitude: float
    start_time: datetime
    escrow_amount_cents: int = Field(500, ge=500, le=2000, description="Between $5 and $20")

class MeetupMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    joined_at: datetime

    class Config:
        from_attributes = True

class MeetupResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    start_time: datetime
    escrow_amount_cents: int
    status: str
    created_at: datetime
    members: List[MeetupMemberResponse] = []
    
    distance_miles: Optional[float] = None # Calculated for nearby queries

    class Config:
        from_attributes = True
