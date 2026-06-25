"""ConsensusResult model — the final agreed-upon state of a trip negotiation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class ConsensusStatus:
    """Consensus result states."""
    ACTIVE = "active"            # Valid consensus, awaiting traveler confirmations
    EXPIRED = "expired"          # TTL expired, needs revalidation
    REVALIDATING = "revalidating"  # Checking if inventory/prices still hold
    INVALIDATED = "invalidated"  # Price drifted or seats gone, renegotiation needed
    CONFIRMED = "confirmed"      # All travelers confirmed
    SUPERSEDED = "superseded"    # Replaced by a newer consensus after renegotiation

    ALL = [ACTIVE, EXPIRED, REVALIDATING, INVALIDATED, CONFIRMED, SUPERSEDED]


class ConsensusResult(Base):
    __tablename__ = "consensus_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=ConsensusStatus.ACTIVE, nullable=False
    )

    # ── Consensus Metrics ────────────────────────────────────────────
    total_cost_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Sum of all travelers' flight costs in cents.",
    )
    max_arrival_spread_actual_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Actual time spread between earliest and latest cluster arrivals.",
    )
    total_negotiation_rounds: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="How many rounds it took to reach consensus.",
    )
    total_tokens_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Total LLM tokens consumed across all rounds.",
    )

    # ── TTL ──────────────────────────────────────────────────────────
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Proposal expires at this time. Auto-revalidation kicks in.",
    )
    confirmation_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="All travelers must confirm by this deadline.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    trip: Mapped["Trip"] = relationship(back_populates="consensus_result")  # noqa: F821
    itineraries: Mapped[list["TravelerItinerary"]] = relationship(  # noqa: F821
        back_populates="consensus", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConsensusResult ${self.total_cost_cents / 100:.2f} spread={self.max_arrival_spread_actual_minutes}m ({self.status})>"
