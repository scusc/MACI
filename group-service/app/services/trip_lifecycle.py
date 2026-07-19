"""
Rally Group Service — Trip Lifecycle State Machine.

Manages transitions between trip states:
  draft → collecting → active → completed
                    ↘ cancelled
"""

import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Trip, TripMember, Payment

logger = logging.getLogger("rally.group.lifecycle")

# Valid state transitions
VALID_TRANSITIONS = {
    "draft": {"collecting", "cancelled"},
    "collecting": {"active", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid state transition."""
    pass


async def transition_trip(
    db: AsyncSession,
    trip: Trip,
    new_status: str,
    reason: str = ""
) -> Trip:
    """
    Transition a trip to a new status with validation.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    current = trip.status
    allowed = VALID_TRANSITIONS.get(current, set())

    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition trip from '{current}' to '{new_status}'. "
            f"Allowed transitions: {allowed or 'none (terminal state)'}"
        )

    old_status = trip.status
    trip.status = new_status
    trip.updated_at = datetime.utcnow()

    logger.info(
        "Trip %s transitioned: %s → %s (reason: %s)",
        trip.id, old_status, new_status, reason or "none"
    )

    return trip


async def check_and_activate(db: AsyncSession, trip: Trip) -> bool:
    """
    Check if a trip's commitment threshold has been met.
    If so, transition to 'active' and return True.

    This should be called after every successful payment.
    """
    if trip.status != "collecting":
        return False

    # Count members (excluding organizer who doesn't need to "commit")
    total_members_result = await db.execute(
        select(func.count(TripMember.id))
        .where(TripMember.trip_id == trip.id)
    )
    total_members = total_members_result.scalar() or 0

    # Count paid members
    paid_members_result = await db.execute(
        select(func.count(TripMember.id))
        .where(TripMember.trip_id == trip.id)
        .where(TripMember.status == "paid")
    )
    paid_count = paid_members_result.scalar() or 0

    if total_members == 0:
        return False

    current_pct = int((paid_count / total_members) * 100)

    logger.info(
        "Trip %s: %d/%d paid (%d%%), threshold: %d%%",
        trip.id, paid_count, total_members, current_pct, trip.threshold_pct
    )

    if current_pct >= trip.threshold_pct:
        await transition_trip(db, trip, "active", reason=f"Threshold met: {current_pct}% >= {trip.threshold_pct}%")
        logger.info("🎉 Trip %s ACTIVATED! Threshold met.", trip.id)
        return True

    return False


async def get_commitment_progress(db: AsyncSession, trip: Trip) -> dict:
    """
    Calculate the current commitment progress for a trip.
    Returns a dict matching the CommitmentProgress schema.
    """
    members = trip.members

    total = len(members)
    committed = sum(1 for m in members if m.status in ("committed", "paid"))
    paid = sum(1 for m in members if m.status == "paid")
    declined = sum(1 for m in members if m.status == "declined")
    pending = total - committed - declined

    amount_collected = sum(m.share_amount or 0 for m in members if m.status == "paid")
    amount_target = sum(m.share_amount or 0 for m in members)

    current_pct = int((paid / total) * 100) if total > 0 else 0

    return {
        "total_members": total,
        "committed_count": committed,
        "paid_count": paid,
        "declined_count": declined,
        "pending_count": pending,
        "threshold_pct": trip.threshold_pct,
        "current_pct": current_pct,
        "threshold_met": current_pct >= trip.threshold_pct,
        "amount_collected": amount_collected,
        "amount_target": amount_target,
    }
