import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models.models import BrandConfig, Trip, TripMember, Payment, User
from maci_core.schemas.rally import (
    BrandConfigCreate,
    BrandConfigResponse,
    OrganizerDashboardStats
)

router = APIRouter(prefix="/organizer", tags=["organizer"])


@router.get("/branding", response_model=BrandConfigResponse)
async def get_branding(
    organizer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the branding configuration for an organizer."""
    result = await db.execute(
        select(BrandConfig).where(BrandConfig.organizer_id == organizer_id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Branding config not found")
    return brand


@router.put("/branding", response_model=BrandConfigResponse)
async def update_branding(
    organizer_id: uuid.UUID,
    config: BrandConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create or update branding configuration."""
    # Ensure organizer exists
    user_result = await db.execute(select(User).where(User.id == organizer_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organizer not found")

    result = await db.execute(
        select(BrandConfig).where(BrandConfig.organizer_id == organizer_id)
    )
    brand = result.scalar_one_or_none()

    if brand:
        brand.primary_color = config.primary_color
        brand.logo_url = config.logo_url
        brand.company_name = config.company_name
    else:
        brand = BrandConfig(
            organizer_id=organizer_id,
            primary_color=config.primary_color,
            logo_url=config.logo_url,
            company_name=config.company_name
        )
        db.add(brand)

    await db.commit()
    await db.refresh(brand)
    return brand


@router.get("/dashboard", response_model=OrganizerDashboardStats)
async def get_dashboard(
    organizer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get high-level business metrics for the organizer."""
    # Ensure organizer exists
    user_result = await db.execute(select(User).where(User.id == organizer_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organizer not found")

    # 1. Total Trips metrics
    trips_result = await db.execute(
        select(Trip.status, func.count(Trip.id))
        .where(Trip.organizer_id == organizer_id)
        .group_by(Trip.status)
    )
    trip_counts = {status: count for status, count in trips_result.all()}
    total_active = trip_counts.get("active", 0) + trip_counts.get("collecting", 0)
    total_completed = trip_counts.get("completed", 0)

    # 2. Revenue and Fees (from Payments)
    # We join Trip and Payment to get payments belonging to the organizer's trips.
    revenue_result = await db.execute(
        select(
            func.sum(Payment.amount),
            func.sum(Payment.platform_fee)
        )
        .join(Trip, Trip.id == Payment.trip_id)
        .where(Trip.organizer_id == organizer_id)
        .where(Payment.status == "released")
    )
    rev_row = revenue_result.first()
    total_amount = rev_row[0] or 0
    total_fees = rev_row[1] or 0
    total_revenue_collected = total_amount - total_fees

    # 3. Upcoming Payouts (payments currently held in escrow)
    payout_result = await db.execute(
        select(
            func.sum(Payment.amount),
            func.sum(Payment.platform_fee)
        )
        .join(Trip, Trip.id == Payment.trip_id)
        .where(Trip.organizer_id == organizer_id)
        .where(Payment.status == "held")
    )
    payout_row = payout_result.first()
    held_amount = payout_row[0] or 0
    held_fees = payout_row[1] or 0
    upcoming_payouts = held_amount - held_fees

    # 4. Conversion Rate (Paid members / Total invited non-organizer members)
    members_result = await db.execute(
        select(TripMember.status, func.count(TripMember.id))
        .join(Trip, Trip.id == TripMember.trip_id)
        .where(Trip.organizer_id == organizer_id)
        .where(TripMember.role == "member")
        .group_by(TripMember.status)
    )
    member_counts = {status: count for status, count in members_result.all()}
    total_members = sum(member_counts.values())
    paid_members = member_counts.get("paid", 0)
    conversion_rate = (paid_members / total_members * 100) if total_members > 0 else 0.0

    return OrganizerDashboardStats(
        total_trips_active=total_active,
        total_trips_completed=total_completed,
        total_revenue_collected=total_revenue_collected,
        total_platform_fees_paid=total_fees,
        average_conversion_rate=conversion_rate,
        upcoming_payouts=upcoming_payouts
    )
