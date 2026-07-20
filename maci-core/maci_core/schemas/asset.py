"""Pydantic schemas for Assets in Slice."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class AssetBase(BaseModel):
    title: str
    description: Optional[str] = None
    asset_type: str
    category: str = "general"
    location: str
    total_price: float
    currency: str = "USD"
    total_slices: int
    media_urls: Optional[List[str]] = None

class AssetCreate(AssetBase):
    external_reference_id: Optional[str] = None

class AssetResponse(AssetBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
