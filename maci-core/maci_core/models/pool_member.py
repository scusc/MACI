"""PoolMember model — represents a user holding a slice in a Pool in Slice."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class PoolMember(Base):
    __tablename__ = "pool_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pools.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # Number of slices this user committed to (usually 1)
    slices_committed: Mapped[int] = mapped_column(Integer, default=1)
    
    # Skill Swapping
    offered_skill: Mapped[str] = mapped_column(String(255), nullable=True)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status: 'pending_approval', 'approved', 'paid', 'rejected', 'withdrawn'
    status: Mapped[str] = mapped_column(String(50), default="pending_approval")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    pool: Mapped["Pool"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="pool_memberships")

    def __repr__(self) -> str:
        return f"<PoolMember {self.user_id} in Pool {self.pool_id}>"
