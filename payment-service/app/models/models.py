"""
Slice Payment Service — SQLAlchemy ORM models.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class Payment(Base):
    __tablename__ = "slice_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    platform_fee = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    gateway = Column(String(20), nullable=False)
    gateway_payment_id = Column(String(200), index=True)
    gateway_transfer_id = Column(String(200))
    status = Column(String(20), nullable=False, default="pending", index=True)
    payment_type = Column(String(20), nullable=False, default="slice_commit")
    escrow_released_at = Column(DateTime(timezone=True))
    refunded_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("gateway IN ('stripe', 'razorpay')", name="chk_payment_gateway"),
        CheckConstraint("status IN ('pending', 'authorized', 'captured', 'refunded', 'failed')", name="chk_payment_status"),
        CheckConstraint("payment_type IN ('slice_commit')", name="chk_payment_type"),
    )
