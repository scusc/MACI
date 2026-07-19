"""
Rally Group Service — Trip & Member API routes.
"""

import logging
import secrets
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.config import settings
from app.models.models import Trip, TripMember, User
from app.services.trip_lifecycle import (
    transition_trip, check_and_activate, get_commitment_progress,
    InvalidTransitionError
)

from maci_core.events.bus import bus_manager
from maci_core.events.schemas import TripThresholdReachedEvent
from maci_core.schemas.rally import (
    TripCreate, TripUpdate, TripResponse, TripListResponse,
    MemberInvite, MemberCommit, MemberDecline,
    MemberSummary, CommitmentProgress,
    TripStatus, MemberStatus, MemberRole, BulkInviteRequest
)

logger = logging.getLogger("rally.group.routes")

router = APIRouter(prefix="/trips", tags=["trips"])


def _generate_invite_code() -> str:
    """Generate a short, URL-safe invite code."""
    return secrets.token_urlsafe(settings.invite_code_length)[:settings.invite_code_length].upper()


def _calculate_fee(amount: int) -> int:
    """Calculate platform fee from share amount."""
    return int(amount * settings.platform_fee_bps / 10000)


async def _get_or_create_user(db: AsyncSession, email: str, display_name: str = None) -> User:
    """Get existing user by email or create a new one."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(email=email, display_name=display_name)
    db.add(user)
    await db.flush()
    return user


def _build_trip_response(trip: Trip, progress: dict) -> TripResponse:
    """Build a TripResponse from ORM model + progress dict."""
    return TripResponse(
        id=trip.id,
        title=trip.title,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        description=trip.description,
        status=TripStatus(trip.status),
        currency=trip.currency,
        threshold_pct=trip.threshold_pct,
        estimated_cost_per_person=trip.estimated_cost_per_person,
        commitment_deadline=trip.commitment_deadline,
        organizer_id=trip.organizer_id,
        invite_code=trip.invite_code,
        members=[
            MemberSummary(
                id=m.id,
                email=m.email,
                display_name=m.display_name,
                role=MemberRole(m.role),
                status=MemberStatus(m.status),
                share_amount=m.share_amount,
                platform_fee=m.platform_fee,
                origin_airport=m.origin_airport,
                committed_at=m.committed_at,
                paid_at=m.paid_at,
            )
            for m in trip.members
        ],
        progress=CommitmentProgress(**progress),
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


async def _load_trip(db: AsyncSession, trip_id: uuid.UUID) -> Trip:
    """Load a trip with all members eagerly loaded."""
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.members))
        .where(Trip.id == trip_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


# ── Trip CRUD ──────────────────────────────────────────────────────────────────

@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    body: TripCreate,
    organizer_email: str = "demo@rally.app",  # TODO: Replace with auth
    db: AsyncSession = Depends(get_db),
):
    """Create a new Rally trip."""
    organizer = await _get_or_create_user(db, organizer_email)

    trip = Trip(
        title=body.title,
        destination=body.destination,
        start_date=body.start_date,
        end_date=body.end_date,
        description=body.description,
        currency=body.currency,
        threshold_pct=body.threshold_pct,
        estimated_cost_per_person=body.estimated_cost_per_person,
        commitment_deadline=body.commitment_deadline,
        invite_code=_generate_invite_code(),
        organizer_id=organizer.id,
    )
    db.add(trip)
    await db.flush()

    # Auto-add organizer as a member with "organizer" role
    organizer_member = TripMember(
        trip_id=trip.id,
        user_id=organizer.id,
        email=organizer.email,
        display_name=organizer.display_name,
        role="organizer",
        status="committed",
        committed_at=datetime.utcnow(),
    )
    db.add(organizer_member)
    await db.flush()

    # Reload with members
    trip = await _load_trip(db, trip.id)
    progress = await get_commitment_progress(db, trip)

    logger.info("Trip created: %s (%s) by %s", trip.title, trip.id, organizer.email)
    return _build_trip_response(trip, progress)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get trip details including member statuses and commitment progress."""
    trip = await _load_trip(db, trip_id)
    progress = await get_commitment_progress(db, trip)
    return _build_trip_response(trip, progress)


@router.get("/invite/{invite_code}", response_model=TripResponse)
async def get_trip_by_invite(invite_code: str, db: AsyncSession = Depends(get_db)):
    """Get trip details by invite code (for shared links)."""
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.members))
        .where(Trip.invite_code == invite_code)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    progress = await get_commitment_progress(db, trip)
    return _build_trip_response(trip, progress)


@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: uuid.UUID,
    body: TripUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update trip details (only in draft or collecting status)."""
    trip = await _load_trip(db, trip_id)

    if trip.status not in ("draft", "collecting"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update trip in '{trip.status}' status"
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trip, field, value)
    trip.updated_at = datetime.utcnow()

    progress = await get_commitment_progress(db, trip)
    return _build_trip_response(trip, progress)


# ── Member Management ──────────────────────────────────────────────────────────

@router.post("/{trip_id}/invite", response_model=TripResponse)
async def invite_members(
    trip_id: uuid.UUID,
    body: MemberInvite,
    db: AsyncSession = Depends(get_db),
):
    """Invite members to a trip. Auto-transitions draft → collecting."""
    trip = await _load_trip(db, trip_id)

    if trip.status not in ("draft", "collecting"):
        raise HTTPException(status_code=400, detail=f"Cannot invite in '{trip.status}' status")

    existing_emails = {m.email for m in trip.members}

    for email in body.emails:
        if email in existing_emails:
            continue
        member = TripMember(
            trip_id=trip.id,
            email=email,
            role="member",
            status="invited",
            share_amount=trip.estimated_cost_per_person,
            platform_fee=_calculate_fee(trip.estimated_cost_per_person or 0),
        )
        db.add(member)

    # Auto-transition to collecting if still in draft
    if trip.status == "draft":
        try:
            await transition_trip(db, trip, "collecting", reason="First invitations sent")
        except InvalidTransitionError:
            pass

    await db.flush()
    trip = await _load_trip(db, trip_id)
    progress = await get_commitment_progress(db, trip)

    logger.info("Invited %d members to trip %s", len(body.emails), trip_id)
    return _build_trip_response(trip, progress)


@router.post("/{trip_id}/bulk-invite", response_model=TripResponse)
async def bulk_invite_members(
    trip_id: uuid.UUID,
    body: BulkInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk invite members to a trip using a JSON payload."""
    trip = await _load_trip(db, trip_id)

    if trip.status not in ("draft", "collecting"):
        raise HTTPException(status_code=400, detail=f"Cannot invite in '{trip.status}' status")

    existing_emails = {m.email for m in trip.members}
    added_count = 0

    for item in body.members:
        if item.email in existing_emails:
            continue
        member = TripMember(
            trip_id=trip.id,
            email=item.email,
            display_name=item.display_name,
            role="member",
            status="invited",
            share_amount=trip.estimated_cost_per_person,
            platform_fee=_calculate_fee(trip.estimated_cost_per_person or 0),
        )
        db.add(member)
        added_count += 1

    # Auto-transition to collecting if still in draft
    if trip.status == "draft" and added_count > 0:
        try:
            await transition_trip(db, trip, "collecting", reason="Bulk invitations sent")
        except InvalidTransitionError:
            pass

    await db.flush()
    trip = await _load_trip(db, trip_id)
    progress = await get_commitment_progress(db, trip)

    logger.info("Bulk invited %d members to trip %s", added_count, trip_id)
    return _build_trip_response(trip, progress)


@router.post("/{trip_id}/members/{member_id}/commit", response_model=TripResponse)
async def commit_member(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberCommit,
    db: AsyncSession = Depends(get_db),
):
    """
    Member commits to the trip. This triggers the payment flow.
    The member's status transitions: invited/viewed → committed.
    Actual payment is handled separately via the payment-service.
    """
    trip = await _load_trip(db, trip_id)

    if trip.status != "collecting":
        raise HTTPException(status_code=400, detail="Trip is not accepting commitments")

    member = next((m for m in trip.members if m.id == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.status not in ("invited", "viewed"):
        raise HTTPException(status_code=400, detail=f"Member already in '{member.status}' state")

    member.status = "committed"
    member.committed_at = datetime.utcnow()
    if body.origin_airport:
        member.origin_airport = body.origin_airport

    logger.info("Member %s committed to trip %s", member.email, trip_id)

    progress = await get_commitment_progress(db, trip)
    return _build_trip_response(trip, progress)


@router.post("/{trip_id}/members/{member_id}/paid", response_model=TripResponse)
async def mark_member_paid(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a member as paid (called by payment-service webhook handler).
    Checks if the trip threshold is now met and activates if so.
    """
    trip = await _load_trip(db, trip_id)

    member = next((m for m in trip.members if m.id == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.status = "paid"
    member.paid_at = datetime.utcnow()

    # Check if threshold is now met
    activated = await check_and_activate(db, trip)

    if activated:
        logger.info("🎉 Trip %s activated after %s paid!", trip_id, member.email)
        
        # Publish event to Service Bus -> triggers Escrow Capture and AI Notifications
        # We need the total amount from members who paid. 
        # For simplicity in this demo, we assume estimated_cost * members.
        # In prod, we sum member.committed_amount.
        total_committed = trip.estimated_cost_per_person * sum(1 for m in trip.members if m.status in ("paid", "committed"))
        
        event = TripThresholdReachedEvent(
            trip_id=str(trip.id),
            trip_title=trip.title,
            organizer_id=str(trip.organizer_id),
            total_committed_amount=total_committed
        )
        await bus_manager.publish_event("trip.threshold.reached", event.model_dump())
        logger.info("Published trip.threshold.reached event to Service Bus")

    progress = await get_commitment_progress(db, trip)
    return _build_trip_response(trip, progress)


@router.post("/{trip_id}/members/{member_id}/decline")
async def decline_member(
    trip_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberDecline,
    db: AsyncSession = Depends(get_db),
):
    """Member declines the trip."""
    trip = await _load_trip(db, trip_id)

    member = next((m for m in trip.members if m.id == member_id), None)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.status in ("paid",):
        raise HTTPException(status_code=400, detail="Cannot decline after payment. Contact organizer for refund.")

    member.status = "declined"
    member.declined_at = datetime.utcnow()

    logger.info("Member %s declined trip %s (reason: %s)", member.email, trip_id, body.reason or "none")
    return {"status": "declined", "member_id": str(member_id)}


# ── Trip Actions ───────────────────────────────────────────────────────────────

@router.post("/{trip_id}/cancel")
async def cancel_trip(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Cancel a trip. Triggers refunds for any held payments."""
    trip = await _load_trip(db, trip_id)

    try:
        await transition_trip(db, trip, "cancelled", reason="Organizer cancelled")
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("Trip %s cancelled. Triggering refunds.", trip_id)
    # TODO: Call payment-service to refund all held payments

    return {"status": "cancelled", "trip_id": str(trip_id)}


@router.get("/{trip_id}/status", response_model=CommitmentProgress)
async def get_trip_status(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get just the commitment progress (lightweight endpoint for polling)."""
    trip = await _load_trip(db, trip_id)
    progress = await get_commitment_progress(db, trip)
    return CommitmentProgress(**progress)
