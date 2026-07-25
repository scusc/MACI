"""User model — represents a B2C traveler in Slice."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from pgvector.sqlalchemy import Vector

from maci_core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Base Identity (Will be moved to encrypted vault in the future)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Zero-Knowledge Profile
    avatar_name: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar_image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # OAuth Identity Anchors
    google_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    apple_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    linkedin_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    
    # Slice specific fields
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_status: Mapped[str] = mapped_column(String(50), default="unverified")  # unverified, pending, verified
    stripe_identity_token: Mapped[str] = mapped_column(String(500), nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True) # For charging the user
    stripe_connect_id: Mapped[str] = mapped_column(String(255), nullable=True)  # For paying the user (if they are a host)
    karma_score: Mapped[float] = mapped_column(Float, default=5.0)
    
    # Trust Passport Subscription Tier ($9.99/mo)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free") # 'free' or 'trust_passport'
    subscription_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    pool_memberships: Mapped[list["PoolMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    psychometric_profile: Mapped["PsychometricProfile"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def get_shielded_profile(self) -> dict:
        """Zero-Knowledge Shielded Profile for public feed before mutual handshake."""
        return {
            "id": str(self.id),
            "display_handle": self.avatar_name or f"Nomad_{str(self.id)[:6]}",
            "avatar_image_url": self.avatar_image_url or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
            "karma_score": self.karma_score,
            "kyc_status": self.kyc_status,
            "subscription_tier": self.subscription_tier,
            "is_identity_shielded": True,
        }

    def get_revealed_profile(self) -> dict:
        """Full Unmasked Identity returned after mutual handshake reveal."""
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": f"{self.first_name} {self.last_name}",
            "avatar_image_url": self.avatar_image_url,
            "karma_score": self.karma_score,
            "kyc_status": self.kyc_status,
            "subscription_tier": self.subscription_tier,
            "linkedin_id": self.linkedin_id,
            "is_identity_shielded": False,
        }

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.id})>"

class PsychometricProfile(Base):
    """
    Stores the user's gamified psychometric quiz answers and their 
    LLM-generated 768-dimensional embedding vector for AI matching.
    """
    __tablename__ = "psychometric_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    
    # 1-10 Scales
    social_battery: Mapped[int] = mapped_column(nullable=False, default=5)
    budget_tolerance: Mapped[int] = mapped_column(nullable=False, default=5)
    pacing: Mapped[int] = mapped_column(nullable=False, default=5)
    spontaneity: Mapped[int] = mapped_column(nullable=False, default=5)
    conflict_style: Mapped[int] = mapped_column(nullable=False, default=5)
    
    # AI Embeddings & Narrative
    structured_bio: Mapped[dict] = mapped_column(JSONB, nullable=True) # e.g. {"travel_ethos": "...", "dealbreakers": "..."}
    embedding: Mapped[dict] = mapped_column(JSONB, nullable=True) # Gemini text-embedding-004 is 768d vector array
    
    # Anti-Cold-Start Logic
    profile_completeness_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 to 100.0

    # Relationships
    user: Mapped["User"] = relationship(back_populates="psychometric_profile")

    def __repr__(self) -> str:
        return f"<PsychometricProfile user_id={self.user_id}>"
