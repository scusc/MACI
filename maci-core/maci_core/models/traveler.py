"""Traveler model — an individual participant in a group trip."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class ConfirmationStatus:
    """Traveler confirmation states."""
    PENDING = "pending"          # Hasn't submitted constraints yet
    SUBMITTED = "submitted"      # Constraints submitted, waiting for negotiation
    PROPOSED = "proposed"        # Itinerary assigned, waiting for confirmation
    CONFIRMED = "confirmed"      # Traveler confirmed their itinerary
    REJECTED = "rejected"        # Traveler rejected their itinerary (triggers renegotiation)

    ALL = [PENDING, SUBMITTED, PROPOSED, CONFIRMED, REJECTED]


class Traveler(Base):
    __tablename__ = "travelers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_iata: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Hard Constraints (deterministic, non-negotiable) ─────────────
    hard_budget_cents: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Maximum budget in cents. Never use floats for money.",
    )
    blocked_windows_utc: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list,
        comment='Array of {"start": "ISO8601", "end": "ISO8601"} UTC windows when traveler CANNOT travel.',
    )

    # ── Soft Preferences (heuristic, fed to LLM) ────────────────────
    soft_preferences: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="Unstructured preferences: seat preference, airline preference, avoid redeye, etc.",
    )

    # ── Status ───────────────────────────────────────────────────────
    confirmation_status: Mapped[str] = mapped_column(
        String(50), default=ConfirmationStatus.PENDING, nullable=False
    )
    constraints_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    trip: Mapped["Trip"] = relationship(back_populates="travelers")  # noqa: F821
    cluster: Mapped["Cluster | None"] = relationship(back_populates="travelers")  # noqa: F821
    itinerary: Mapped["TravelerItinerary | None"] = relationship(  # noqa: F821
        back_populates="traveler", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Traveler {self.name} from {self.origin_iata} ({self.confirmation_status})>"
