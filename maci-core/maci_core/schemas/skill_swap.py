"""
Skill Swap Schemas — Pydantic models for pod barter in Rally.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from maci_core.models.skill_swap import SkillCategory, SwapStatus


class PodSkillCreate(BaseModel):
    category: SkillCategory
    title: str
    description: Optional[str] = None
    estimated_value_cents: int = 0


class PodSkillResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    user_id: uuid.UUID
    category: SkillCategory
    title: str
    description: Optional[str]
    estimated_value_cents: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillSwapRequestCreate(BaseModel):
    skill_id: uuid.UUID
    target_user_id: Optional[uuid.UUID] = None
    offset_amount_cents: int
    note: Optional[str] = None


class SkillSwapRequestResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    skill_id: uuid.UUID
    offered_by_user_id: uuid.UUID
    target_user_id: Optional[uuid.UUID]
    offset_amount_cents: int
    status: SwapStatus
    note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
