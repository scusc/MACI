"""Pydantic schemas for Payments in Slice."""

from enum import Enum
from uuid import UUID
from pydantic import BaseModel

class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"

class PaymentType(str, Enum):
    SLICE_COMMIT = "slice_commit"

class PaymentCreate(BaseModel):
    pool_id: UUID
    member_id: UUID
    amount: float
    currency: str = "USD"
    gateway: PaymentGateway
    payment_type: PaymentType = PaymentType.SLICE_COMMIT

class PaymentResponse(BaseModel):
    id: UUID
    gateway_payment_id: str

class EscrowRelease(BaseModel):
    pool_id: UUID
    amount_released: float
    status: str

class RefundResult(BaseModel):
    pool_id: UUID
    amount_refunded: float
    status: str
