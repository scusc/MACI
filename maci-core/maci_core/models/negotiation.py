"""NegotiationRound model — audit trail for every LLM interaction."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base


class RoundStatus:
    """Negotiation round states."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Cluster constraints unchanged, LLM call skipped

    ALL = [IN_PROGRESS, COMPLETED, FAILED, SKIPPED]


class NegotiationRound(Base):
    __tablename__ = "negotiation_rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=RoundStatus.IN_PROGRESS, nullable=False
    )

    # ── LLM Audit Trail ──────────────────────────────────────────────
    # Full snapshots of what the LLM saw and what it produced.
    # Critical for debugging, cost tracking, and prompt engineering.
    llm_input_snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Exact payload sent to the LLM (system prompt + user message).",
    )
    llm_output_snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Raw LLM response before Pydantic validation.",
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Total tokens consumed (prompt + completion).",
    )

    # ── Convergence Feedback ─────────────────────────────────────────
    convergence_adjustment: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Adjustment hint from orchestrator if convergence failed.",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    cluster: Mapped["Cluster"] = relationship(back_populates="negotiation_rounds")  # noqa: F821
    proposals: Mapped[list["FlightProposal"]] = relationship(  # noqa: F821
        back_populates="round", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<NegotiationRound #{self.round_number} for cluster {self.cluster_id} ({self.status})>"
