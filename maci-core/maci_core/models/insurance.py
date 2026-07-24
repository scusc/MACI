import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from maci_core.database import Base

class InsuranceStatus(str, enum.Enum):
    active = "active"
    claimed = "claimed"
    expired = "expired"
    cancelled = "cancelled"

class InsurancePolicy(Base):
    """
    Travel Insurance attached to a specific Trip/Pool to cover emergency cancellations.
    """
    __tablename__ = "insurance_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    coverage_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    premium_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    
    status: Mapped[InsuranceStatus] = mapped_column(Enum(InsuranceStatus), default=InsuranceStatus.active)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pool = relationship("Pool")
