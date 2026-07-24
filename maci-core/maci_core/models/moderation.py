import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from maci_core.database import Base

class ReportStatus(str, enum.Enum):
    pending = "pending"
    investigating = "investigating"
    resolved_action_taken = "resolved_action_taken"
    resolved_no_action = "resolved_no_action"

class ReportReason(str, enum.Enum):
    inappropriate_behavior = "inappropriate_behavior"
    spam_or_scam = "spam_or_scam"
    safety_concern = "safety_concern"
    fake_profile = "fake_profile"
    other = "other"

class Report(Base):
    """
    Moderation Pillar: Allows users to report other users securely.
    """
    __tablename__ = "moderation_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reported_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Optional connection ID if the report happened during a chat/trip
    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_connections.id", ondelete="SET NULL"), nullable=True)
    
    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Ban(Base):
    """
    Tracks administrative bans for toxic users to protect the ecosystem.
    """
    __tablename__ = "moderation_bans"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
