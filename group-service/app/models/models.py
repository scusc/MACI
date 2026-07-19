"""
Rally Group Service — SQLAlchemy ORM models.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Text, ForeignKey,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "rally_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True) # Nullable for lazy users created by invites
    display_name = Column(String(100))
    phone = Column(String(20))
    country_code = Column(String(2), default="US")
    stripe_customer_id = Column(String(100))
    razorpay_customer_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organized_trips = relationship("Trip", back_populates="organizer")
    memberships = relationship("TripMember", back_populates="user")
    brand_config = relationship("BrandConfig", back_populates="organizer", uselist=False, cascade="all, delete-orphan")


class BrandConfig(Base):
    __tablename__ = "rally_brand_configs"

    organizer_id = Column(UUID(as_uuid=True), ForeignKey("rally_users.id", ondelete="CASCADE"), primary_key=True)
    primary_color = Column(String(7), nullable=False, default="#000000")
    logo_url = Column(String(1000))
    company_name = Column(String(100), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organizer = relationship("User", back_populates="brand_config")


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
    estimated_cost_per_person = Column(Integer)  # cents/paise
    commitment_deadline = Column(DateTime(timezone=True))
    invite_code = Column(String(20), unique=True, nullable=False, index=True)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("rally_users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'collecting', 'active', 'completed', 'cancelled')", name="chk_trip_status"),
        CheckConstraint("threshold_pct >= 50 AND threshold_pct <= 100", name="chk_threshold"),
    )

    # Relationships
    organizer = relationship("User", back_populates="organized_trips")
    members = relationship("TripMember", back_populates="trip", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="trip")
    price_snapshots = relationship("PriceSnapshot", back_populates="trip", cascade="all, delete-orphan")


class TripMember(Base):
    __tablename__ = "rally_trip_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("rally_trips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("rally_users.id"), index=True)
    email = Column(String(255), nullable=False)
    display_name = Column(String(100))
    role = Column(String(20), nullable=False, default="member")
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
        UniqueConstraint("trip_id", "email", name="uq_trip_member_email"),
        CheckConstraint("role IN ('organizer', 'member')", name="chk_member_role"),
        CheckConstraint("status IN ('invited', 'viewed', 'committed', 'paid', 'declined')", name="chk_member_status"),
    )

    # Relationships
    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="memberships")
    payments = relationship("Payment", back_populates="member")


class Payment(Base):
    __tablename__ = "rally_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("rally_trips.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("rally_trip_members.id"), nullable=False, index=True)
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
    trip = relationship("Trip", back_populates="payments")
    member = relationship("TripMember", back_populates="payments")


class PriceSnapshot(Base):
    __tablename__ = "rally_price_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("rally_trips.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_airport = Column(String(3), nullable=False)
    estimated_price = Column(Integer, nullable=False)  # cents
    snapshot_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="price_snapshots")
