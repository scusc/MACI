"""Trip model — a single group travel coordination session."""

import uuid
import secrets
from datetime import datetime, timezone, date

from sqlalchemy import String, Date, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class TripStatus:
    """Trip lifecycle states."""
    DRAFT = "draft"
    INTAKE_OPEN = "intake_open"
    CLUSTERING = "clustering"
    NEGOTIATING = "negotiating"
    CONSENSUS_REACHED = "consensus_reached"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RENEGOTIATING = "renegotiating"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"

    ALL = [
        DRAFT, INTAKE_OPEN, CLUSTERING, NEGOTIATING,
        CONSENSUS_REACHED, AWAITING_CONFIRMATION,
        RENEGOTIATING, CONFIRMED, COMPLETED, FAILED,
    ]


def _generate_intake_token() -> str:
    """Generate a URL-safe intake token for sharing."""
    return f"maci_{secrets.token_urlsafe(16)}"


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_city: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_iata: Mapped[str] = mapped_column(String(10), nullable=False)
    arrival_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_arrival_spread_minutes: Mapped[int] = mapped_column(
        Integer, default=120, nullable=False
    )
    friction_weight_cents: Mapped[int] = mapped_column(
        Integer, default=2500, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=TripStatus.DRAFT, nullable=False
    )
    intake_token: Mapped[str] = mapped_column(
        String(100), default=_generate_intake_token, unique=True, nullable=False
    )
    intake_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_travelers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="trips")  # noqa: F821
    travelers: Mapped[list["Traveler"]] = relationship(  # noqa: F821
        back_populates="trip", cascade="all, delete-orphan"
    )
    clusters: Mapped[list["Cluster"]] = relationship(  # noqa: F821
        back_populates="trip", cascade="all, delete-orphan"
    )
    consensus_result: Mapped["ConsensusResult | None"] = relationship(  # noqa: F821
        back_populates="trip", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Trip '{self.title}' → {self.destination_iata} ({self.status})>"
