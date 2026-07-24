"""
Skill Swap Models — Pod Barter & Skill-Swapping Micro-Economy in Rally.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from maci_core.database import Base


class SkillCategory(str, enum.Enum):
    photography = "photography"
    language = "language"
    driving = "driving"
    cooking = "cooking"
    logistics = "logistics"
    fitness = "fitness"
    other = "other"


class SwapStatus(str, enum.Enum):
    proposed = "proposed"
    accepted = "accepted"
    declined = "declined"
    completed = "completed"


class PodSkill(Base):
    """
    Represents a verified skill offered by a traveler within a specific trip/pod.
    """
    __tablename__ = "pod_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    category: Mapped[SkillCategory] = mapped_column(Enum(SkillCategory), nullable=False, default=SkillCategory.other)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    estimated_value_cents: Mapped[int] = mapped_column(Integer, default=0) # Value offered to offset share
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class SkillSwapRequest(Base):
    """
    Represents a proposed barter exchange where traveler A provides a skill to traveler B
    or the group in exchange for a discount/offset on shared accommodation costs.
    """
    __tablename__ = "skill_swap_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pod_skills.id", ondelete="CASCADE"), nullable=False)
    
    offered_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True) # Null if group-wide swap
    
    offset_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[SwapStatus] = mapped_column(Enum(SwapStatus), default=SwapStatus.proposed)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    skill = relationship("PodSkill")
    offered_by = relationship("User", foreign_keys=[offered_by_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
