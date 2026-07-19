"""
Rally Platform Schemas — Pydantic models for the group commitment & payment platform.

These models define the API contracts for Rally's core services:
  - Trip creation, lifecycle, and member management
  - Payment processing, escrow, and cost splitting
  - Price alerts and cost estimation
"""

import uuid
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class TripStatus(str, Enum):
    """Trip lifecycle states."""
    DRAFT = "draft"
    COLLECTING = "collecting"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MemberStatus(str, Enum):
    """Member commitment states."""
    INVITED = "invited"
    VIEWED = "viewed"
    COMMITTED = "committed"
    PAID = "paid"
    DECLINED = "declined"


class MemberRole(str, Enum):
    ORGANIZER = "organizer"
    MEMBER = "member"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    HELD = "held"          # Authorized but not captured (escrow)
    RELEASED = "released"  # Captured / settled to organizer
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentType(str, Enum):
    DEPOSIT = "deposit"
    INSTALLMENT = "installment"
    FINAL = "final"


class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"


# ── Trip Schemas ───────────────────────────────────────────────────────────────

class TripCreate(BaseModel):
    """Input schema for creating a Rally trip."""
    title: str = Field(..., min_length=3, max_length=200, examples=["Barcelona Crew Trip 2026"])
    destination: str = Field(..., min_length=2, max_length=200, examples=["Barcelona, Spain"])
    start_date: date = Field(..., examples=["2026-09-16"])
    end_date: Optional[date] = Field(None, examples=["2026-09-20"])
    description: Optional[str] = Field(None, max_length=2000)
    currency: str = Field(default="USD", pattern="^(USD|INR|EUR|GBP)$")
    threshold_pct: int = Field(
        default=80, ge=50, le=100,
        description="Percentage of members who must commit+pay for the trip to activate"
    )
    estimated_cost_per_person: Optional[int] = Field(
        None, ge=0,
        description="Estimated cost per person in smallest currency unit (cents/paise)"
    )
    commitment_deadline: Optional[datetime] = Field(
        None,
        description="UTC deadline for members to commit. Trip auto-cancels if threshold not met."
    )


class TripUpdate(BaseModel):
    """Partial update for a trip (only in draft/collecting status)."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    destination: Optional[str] = Field(None, min_length=2, max_length=200)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    currency: Optional[str] = Field(None, pattern="^(USD|INR|EUR|GBP)$")
    threshold_pct: Optional[int] = Field(None, ge=50, le=100)
    estimated_cost_per_person: Optional[int] = Field(None, ge=0)
    commitment_deadline: Optional[datetime] = None


class MemberSummary(BaseModel):
    """Summary of a trip member's status."""
    id: uuid.UUID
    email: str
    display_name: Optional[str] = None
    role: MemberRole
    status: MemberStatus
    share_amount: Optional[int] = None     # cents/paise
    platform_fee: Optional[int] = None     # cents/paise
    origin_airport: Optional[str] = None
    committed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CommitmentProgress(BaseModel):
    """Current commitment progress for a trip."""
    total_members: int
    committed_count: int
    paid_count: int
    declined_count: int
    pending_count: int
    threshold_pct: int
    current_pct: int
    threshold_met: bool
    amount_collected: int         # cents/paise
    amount_target: int            # cents/paise


class TripResponse(BaseModel):
    """Full trip details returned in API responses."""
    id: uuid.UUID
    title: str
    destination: str
    start_date: date
    end_date: Optional[date]
    description: Optional[str]
    status: TripStatus
    currency: str
    threshold_pct: int
    estimated_cost_per_person: Optional[int]
    commitment_deadline: Optional[datetime]
    organizer_id: uuid.UUID
    invite_code: str              # Shareable invite code/link
    members: List[MemberSummary]
    progress: CommitmentProgress
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripListResponse(BaseModel):
    """Paginated trip list."""
    trips: List[TripResponse]
    total: int


# ── Member Schemas ─────────────────────────────────────────────────────────────

class MemberInvite(BaseModel):
    """Invite one or more members to a trip."""
    emails: List[str] = Field(..., min_length=1, max_length=50)
    message: Optional[str] = Field(None, max_length=500, description="Personal message from organizer")


class MemberCommit(BaseModel):
    """Member commits to a trip (triggers payment flow)."""
    origin_airport: Optional[str] = Field(None, min_length=3, max_length=3, description="IATA code")


class MemberDecline(BaseModel):
    """Member declines a trip."""
    reason: Optional[str] = Field(None, max_length=500)


# ── Payment Schemas ────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    """Request to create a payment for a trip member."""
    trip_id: uuid.UUID
    member_id: uuid.UUID
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit (cents/paise)")
    currency: str = Field(default="USD", pattern="^(USD|INR|EUR|GBP)$")
    gateway: PaymentGateway
    payment_type: PaymentType = PaymentType.DEPOSIT


class PaymentResponse(BaseModel):
    """Payment details returned after creation."""
    id: uuid.UUID
    trip_id: uuid.UUID
    member_id: uuid.UUID
    amount: int
    platform_fee: int
    currency: str
    gateway: PaymentGateway
    status: PaymentStatus
    payment_type: PaymentType
    # Gateway-specific fields for frontend
    stripe_client_secret: Optional[str] = None      # For Stripe Elements
    razorpay_order_id: Optional[str] = None          # For Razorpay Checkout
    razorpay_key_id: Optional[str] = None            # Public key for frontend
    created_at: datetime

    model_config = {"from_attributes": True}


class EscrowRelease(BaseModel):
    """Result of escrow release operation."""
    trip_id: uuid.UUID
    total_released: int           # cents/paise
    payments_released: int        # count
    gateway_transfer_ids: List[str]


class RefundResult(BaseModel):
    """Result of a refund operation."""
    trip_id: uuid.UUID
    total_refunded: int
    payments_refunded: int
    failed_refunds: List[str]     # payment IDs that failed to refund


# ── Cost Estimation Schemas ────────────────────────────────────────────────────

class CostEstimateRequest(BaseModel):
    """Request AI-powered cost estimation for a trip."""
    destination: str
    start_date: date
    end_date: Optional[date]
    origins: List[str] = Field(..., description="IATA codes of member origins")
    num_travelers: int = Field(..., ge=1)


class OriginCostBreakdown(BaseModel):
    """Estimated cost for travelers from a specific origin."""
    origin_airport: str
    estimated_flight_cost: int    # cents, per person
    price_level: Optional[str]    # "low", "typical", "high"
    confidence: str = "estimate"  # "estimate" or "quoted"


class CostEstimateResponse(BaseModel):
    """AI-generated cost estimate for the group."""
    destination: str
    flight_estimates: List[OriginCostBreakdown]
    estimated_hotel_per_night: Optional[int]   # cents, per person
    estimated_total_per_person: int             # cents, average across origins
    price_trend: Optional[str]                  # "rising", "stable", "falling"
    recommendation: Optional[str]              # "Book now" / "Wait 3 days"


# ── Price Alert Schemas ────────────────────────────────────────────────────────

class PriceSnapshot(BaseModel):
    """A point-in-time price snapshot for tracking cost of delay."""
    trip_id: uuid.UUID
    origin_airport: str
    estimated_price: int          # cents
    snapshot_at: datetime


class PriceAlert(BaseModel):
    """Price change alert sent to the group."""
    trip_id: uuid.UUID
    origin_airport: str
    previous_price: int
    current_price: int
    change_pct: float
    direction: str                # "up" or "down"
    cumulative_change_since_creation: int  # Total cost of delay
    message: str                  # AI-generated alert message

# ── B2B2C Schemas ──────────────────────────────────────────────────────────────

class BrandConfigCreate(BaseModel):
    """Update or create branding for an organizer."""
    primary_color: str = Field(..., pattern="^#[0-9A-Fa-f]{6}$")
    logo_url: Optional[str] = None
    company_name: str = Field(..., min_length=2, max_length=100)


class BrandConfigResponse(BaseModel):
    """Branding configuration details."""
    organizer_id: uuid.UUID
    primary_color: str
    logo_url: Optional[str]
    company_name: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkInviteItem(BaseModel):
    """Single item in a bulk invite."""
    email: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None


class BulkInviteRequest(BaseModel):
    """Request to bulk invite members (JSON format)."""
    members: List[BulkInviteItem]
    message: Optional[str] = None


class OrganizerDashboardStats(BaseModel):
    """High-level metrics for the organizer."""
    total_trips_active: int
    total_trips_completed: int
    total_revenue_collected: int      # cents (amount paid minus platform fees)
    total_platform_fees_paid: int     # cents
    average_conversion_rate: float    # percentage (0-100)
    upcoming_payouts: int             # cents (escrow held that will release soon)
