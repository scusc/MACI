"""TravelerItinerary model — maps a traveler to their assigned flight from the consensus."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class ItineraryConfirmation:
    """Traveler confirmation states for their specific itinerary."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    BOOKED = "booked"  # Traveler reports they've manually booked

    ALL = [PENDING, CONFIRMED, REJECTED, BOOKED]


class TravelerItinerary(Base):
    __tablename__ = "traveler_itineraries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consensus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consensus_results.id", ondelete="CASCADE"), nullable=False
    )
    traveler_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("travelers.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("flight_proposals.id", ondelete="SET NULL"), nullable=True
    )

    # ── Booking Execution ────────────────────────────────────────────
    booking_deep_link: Mapped[str | None] = mapped_column(
        String(2000), nullable=True,
        comment="Direct URL for this traveler to book their assigned flight.",
    )
    traveler_confirmation: Mapped[str] = mapped_column(
        String(50), default=ItineraryConfirmation.PENDING, nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    consensus: Mapped["ConsensusResult"] = relationship(back_populates="itineraries")  # noqa: F821
    traveler: Mapped["Traveler"] = relationship(back_populates="itinerary")  # noqa: F821

    def __repr__(self) -> str:
        return f"<TravelerItinerary for {self.traveler_id} ({self.traveler_confirmation})>"
