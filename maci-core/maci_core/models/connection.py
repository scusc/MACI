import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from maci_core.database import Base

class ConnectionStatus(str, enum.Enum):
    anonymous = "anonymous"
    voice_unlocked = "voice_unlocked"
    identity_revealed = "identity_revealed"
    blocked = "blocked"

class MatchConnection(Base):
    """
    Represents a 1-on-1 match between two users. Tracks the Progressive 
    Trust Handshake state (anonymous -> voice -> revealed).
    """
    __tablename__ = "match_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # We store the lower UUID in user_a_id to prevent duplicates
    user_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus), default=ConnectionStatus.anonymous)
    
    # Mutual Smart Contract Voting
    user_a_reveal_vote: Mapped[bool] = mapped_column(Boolean, default=False)
    user_b_reveal_vote: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user_a = relationship("User", foreign_keys=[user_a_id])
    user_b = relationship("User", foreign_keys=[user_b_id])
    messages = relationship("ChatMessage", back_populates="connection", cascade="all, delete-orphan")

class ChatMessage(Base):
    """
    Stores individual messages inside a MatchConnection. Supports text or audio.
    """
    __tablename__ = "chat_messages"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_connections.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    content_text: Mapped[str] = mapped_column(Text, nullable=True)
    audio_uri: Mapped[str] = mapped_column(String(1000), nullable=True) # Used if voice note
    
    is_system_message: Mapped[bool] = mapped_column(Boolean, default=False) # e.g., "Identities Revealed!"
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    connection = relationship("MatchConnection", back_populates="messages")
    sender = relationship("User")
