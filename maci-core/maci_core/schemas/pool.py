"""Pydantic schemas for Pools in Slice."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class PoolBase(BaseModel):
    start_date: datetime
    end_date: datetime
    funding_deadline: datetime
    require_vibe_check: bool = True

class PoolCreate(PoolBase):
    asset_id: UUID

class PoolResponse(PoolBase):
    id: UUID
    asset_id: UUID
    host_id: UUID
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
