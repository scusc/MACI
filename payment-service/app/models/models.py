"""
Slice Payment Service — SQLAlchemy ORM models for Swarm Treasury.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Boolean,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class SwarmTreasury(Base):
    __tablename__ = "slice_swarm_treasuries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swarm_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    balance = Column(Integer, nullable=False, default=0) # cents
    currency = Column(String(3), nullable=False, default="USD")
    virtual_card_id = Column(String(100)) # e.g. Stripe Issuing Card ID
    virtual_card_last4 = Column(String(4))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = relationship("TreasuryTransaction", back_populates="treasury")


class TreasuryTransaction(Base):
    __tablename__ = "slice_treasury_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    treasury_id = Column(UUID(as_uuid=True), ForeignKey("slice_swarm_treasuries.id"), nullable=False, index=True)
    peer_id = Column(UUID(as_uuid=True), nullable=True, index=True) # Null if external vendor charge
    amount = Column(Integer, nullable=False) # Positive = Deposit, Negative = Spend
    currency = Column(String(3), nullable=False, default="USD")
    transaction_type = Column(String(20), nullable=False) # 'deposit', 'card_spend', 'refund'
    gateway_reference = Column(String(200), index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("transaction_type IN ('deposit', 'card_spend', 'refund')", name="chk_txn_type"),
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'reversed')", name="chk_txn_status"),
    )

    treasury = relationship("SwarmTreasury", back_populates="transactions")

class Payment(Base):
    __tablename__ = "slice_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), index=True)
    member_id = Column(UUID(as_uuid=True), index=True)
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
