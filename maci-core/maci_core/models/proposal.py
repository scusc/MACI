"""FlightProposal model — a specific flight option selected by an AI delegate."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class ProposalStatus:
    """Flight proposal states."""
    PROPOSED = "proposed"        # Selected by AI delegate
    ACCEPTED = "accepted"        # Passed convergence check
    REJECTED = "rejected"        # Failed convergence or constraint check
    EXPIRED = "expired"          # TTL expired, inventory may have rotted
    SELECTED = "selected"        # Part of final consensus

    ALL = [PROPOSED, ACCEPTED, REJECTED, EXPIRED, SELECTED]


class FlightProposal(Base):
    __tablename__ = "flight_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("negotiation_rounds.id", ondelete="CASCADE"), nullable=False
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False
    )

    # ── Flight Details ───────────────────────────────────────────────
    flight_number: Mapped[str] = mapped_column(String(20), nullable=False)
    airline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_iata: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_iata: Mapped[str] = mapped_column(String(10), nullable=False)
    departure_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    stops: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    layover_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cabin_class: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Pricing ──────────────────────────────────────────────────────
    price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Price per person in cents.",
    )
    total_cost_score: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Friction-adjusted total cost: price + (layover_hours × friction_weight).",
    )

    # ── Availability ─────────────────────────────────────────────────
    available_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_source: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="'amadeus', 'duffel', or 'serpapi'.",
    )
    provider_booking_id: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Provider-specific ID for deep-linking to exact fare.",
    )
    booking_deep_link: Mapped[str | None] = mapped_column(
        String(2000), nullable=True,
        comment="Direct URL to book this exact flight.",
    )

    # ── Status & Raw Data ────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50), default=ProposalStatus.PROPOSED, nullable=False
    )
    raw_provider_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Full provider API response for debugging and audit.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    round: Mapped["NegotiationRound"] = relationship(back_populates="proposals")  # noqa: F821

    def __repr__(self) -> str:
        return f"<FlightProposal {self.flight_number} ${self.price_cents / 100:.2f} ({self.status})>"
