"""Asset model — represents a luxury travel asset (villa, yacht, etc) in Slice."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 'villa', 'yacht'
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general") # e.g. 'luxury', 'budget', 'adventure'
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Pricing and Capacity
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    total_slices: Mapped[int] = mapped_column(nullable=False)
    
    # Store external API references (e.g., Expedia Property ID)
    external_reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_urls: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    pools: Mapped[list["Pool"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset {self.title} ({self.id})>"
