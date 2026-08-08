"""
Rally Group Service — SQLAlchemy ORM models.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime, Text, ForeignKey,
    UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Read-only reference to auth-service users table. Do NOT create/modify users here."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    display_name = Column(String(100))
    kyc_status = Column(String(50), default="unverified")
    karma_score = Column(Float, default=5.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    swarm_peers = relationship("SwarmPeer", back_populates="user")
    trust_graph = relationship("TrustGraph", back_populates="user", uselist=False, cascade="all, delete-orphan")


class TrustGraph(Base):
    __tablename__ = "rally_trust_graphs"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    verified_domain = Column(String(255))
    instagram_handle = Column(String(100))
    linkedin_id = Column(String(100))
    trust_score = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="trust_graph")


class Swarm(Base):
    __tablename__ = "rally_swarms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="draft", index=True)
    currency = Column(String(3), nullable=False, default="USD")
    threshold_pct = Column(Integer, nullable=False, default=80)
    estimated_cost_per_person = Column(Integer)  # cents/paise
    commitment_deadline = Column(DateTime(timezone=True))
    invite_code = Column(String(20), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'collecting', 'active', 'completed', 'cancelled')", name="chk_swarm_status"),
        CheckConstraint("threshold_pct >= 50 AND threshold_pct <= 100", name="chk_threshold"),
    )

    # Relationships
    peers = relationship("SwarmPeer", back_populates="swarm", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="swarm")
    price_snapshots = relationship("PriceSnapshot", back_populates="swarm", cascade="all, delete-orphan")


class SwarmPeer(Base):
    __tablename__ = "rally_swarm_peers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swarm_id = Column(UUID(as_uuid=True), ForeignKey("rally_swarms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    email = Column(String(255), nullable=False)
    display_name = Column(String(100))
    role = Column(String(20), nullable=False, default="peer")
    status = Column(String(20), nullable=False, default="invited", index=True)
    share_amount = Column(Integer)     # cents/paise
    platform_fee = Column(Integer)     # cents/paise
    origin_airport = Column(String(3))
    invited_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    viewed_at = Column(DateTime(timezone=True))
    committed_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    declined_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("swarm_id", "email", name="uq_swarm_peer_email"),
        CheckConstraint("role IN ('peer')", name="chk_peer_role"),
        CheckConstraint("status IN ('invited', 'viewed', 'committed', 'paid', 'declined')", name="chk_peer_status"),
    )

    # Relationships
    swarm = relationship("Swarm", back_populates="peers")
    user = relationship("User", back_populates="swarm_peers")
    payments = relationship("Payment", back_populates="peer")


class Payment(Base):
    __tablename__ = "rally_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swarm_id = Column(UUID(as_uuid=True), ForeignKey("rally_swarms.id"), nullable=False, index=True)
    peer_id = Column(UUID(as_uuid=True), ForeignKey("rally_swarm_peers.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    platform_fee = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    gateway = Column(String(20), nullable=False)
    gateway_payment_id = Column(String(200), index=True)
    gateway_transfer_id = Column(String(200))
    status = Column(String(20), nullable=False, default="pending", index=True)
    payment_type = Column(String(20), nullable=False, default="deposit")
    escrow_released_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("gateway IN ('stripe', 'razorpay')", name="chk_payment_gateway"),
        CheckConstraint("status IN ('pending', 'held', 'released', 'refunded', 'failed')", name="chk_payment_status"),
        CheckConstraint("payment_type IN ('deposit', 'installment', 'final')", name="chk_payment_type"),
    )

    # Relationships
    swarm = relationship("Swarm", back_populates="payments")
    peer = relationship("SwarmPeer", back_populates="payments")


class PriceSnapshot(Base):
    __tablename__ = "rally_price_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swarm_id = Column(UUID(as_uuid=True), ForeignKey("rally_swarms.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_airport = Column(String(3), nullable=False)
    estimated_price = Column(Integer, nullable=False)  # cents
    snapshot_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    swarm = relationship("Swarm", back_populates="price_snapshots")

class Trip(Base):
    __tablename__ = "rally_trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="draft", index=True)
    currency = Column(String(3), nullable=False, default="USD")
    threshold_pct = Column(Integer, nullable=False, default=80)
    estimated_cost_per_person = Column(Integer)
    commitment_deadline = Column(DateTime(timezone=True))
    invite_code = Column(String(20), unique=True, nullable=False, index=True)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    members = relationship("TripMember", back_populates="trip", cascade="all, delete-orphan")


class TripMember(Base):
    __tablename__ = "rally_trip_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("rally_trips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    email = Column(String(255), nullable=False)
    display_name = Column(String(100))
    role = Column(String(20), nullable=False, default="member")
    status = Column(String(20), nullable=False, default="invited", index=True)
    share_amount = Column(Integer)
    platform_fee = Column(Integer)
    origin_airport = Column(String(3))
    committed_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    declined_at = Column(DateTime(timezone=True))

    trip = relationship("Trip", back_populates="members")


class BrandConfig(Base):
    __tablename__ = "rally_brand_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    brand_name = Column(String(100))
    logo_url = Column(String(500))
    primary_color = Column(String(20))
    secondary_color = Column(String(20))
    tagline = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
