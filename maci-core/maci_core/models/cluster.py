"""Cluster model — a group of travelers with shared origin constraints."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class ClusterStatus:
    """Cluster lifecycle states."""
    FORMED = "formed"            # Cluster created by MapReduce
    SEARCHING = "searching"      # Delegate searching for flights
    PROPOSED = "proposed"        # Flight proposed, awaiting convergence
    ADJUSTING = "adjusting"      # Orchestrator requested arrival adjustment
    CONVERGED = "converged"      # Part of final consensus
    FAILED = "failed"            # No viable options found

    ALL = [FORMED, SEARCHING, PROPOSED, ADJUSTING, CONVERGED, FAILED]


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    origin_iata: Mapped[str] = mapped_column(String(10), nullable=False)
    cluster_key: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Composite key: '{origin_iata}_{date_bucket}' for grouping.",
    )
    traveler_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=ClusterStatus.FORMED, nullable=False
    )

    # ── Aggregated Constraints ───────────────────────────────────────
    # Pre-computed from all travelers in this cluster during formation.
    aggregated_constraints: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="Pre-computed: min budget, latest unblock time, earliest departure, seat count.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    trip: Mapped["Trip"] = relationship(back_populates="clusters")  # noqa: F821
    travelers: Mapped[list["Traveler"]] = relationship(back_populates="cluster")  # noqa: F821
    negotiation_rounds: Mapped[list["NegotiationRound"]] = relationship(  # noqa: F821
        back_populates="cluster", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cluster {self.cluster_key} ({self.traveler_count} travelers, {self.status})>"
