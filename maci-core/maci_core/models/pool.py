"""Pool model — represents a group of users funding an asset in Slice."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class Pool(Base):
    __tablename__ = "pools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # Status: 'open', 'funding', 'locked', 'confirmed', 'booked', 'completed', 'failed'
    status: Mapped[str] = mapped_column(String(50), default="funding")
    require_vibe_check: Mapped[bool] = mapped_column(default=True)
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    funding_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="pools")
    host: Mapped["User"] = relationship()
    members: Mapped[list["PoolMember"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )
    messages: Mapped[list["PoolMessage"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Pool {self.id} Status: {self.status}>"
