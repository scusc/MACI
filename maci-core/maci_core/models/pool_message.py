import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from maci_core.database import Base

class PoolMessage(Base):
    """
    Stores individual messages inside a travel Pool (Group Chat).
    """
    __tablename__ = "pool_messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False)
    
    # sender_id can be null if it's an AI or System message
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    sender_name: Mapped[str] = mapped_column(String(255), nullable=True) # E.g., 'Slice AI', 'System Mediator'
    content_text: Mapped[str] = mapped_column(Text, nullable=True)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pool = relationship("Pool", back_populates="messages")
    sender = relationship("User")
