"""
Rally Group Service — Trip Lifecycle Module.

Provides Trip-specific lifecycle functions, overriding the swarm-based versions.
"""

from app.services.swarm_lifecycle import (
    transition_swarm as transition_trip,
    check_and_activate,
    InvalidTransitionError,
    update_karma
)
from app.models.models import Trip


async def get_commitment_progress(db, trip: Trip) -> dict:
    """
    Calculate commitment progress for a Trip.
    Uses trip.members (TripMember objects) instead of swarm.peers.
    Returns keys matching the CommitmentProgress schema.
    """
    members = trip.members if hasattr(trip, 'members') and trip.members is not None else []
    total_members = len(members)
    committed_count = sum(1 for m in members if m.status in ("committed", "paid"))
    paid_count = sum(1 for m in members if m.status == "paid")
    declined_count = sum(1 for m in members if m.status == "declined")
    pending_count = sum(1 for m in members if m.status == "pending")
    amount_collected = sum(m.share_amount or 0 for m in members if m.status == "paid")

    threshold_pct = getattr(trip, 'threshold_pct', 80)
    max_size = getattr(trip, 'max_group_size', None) or max(total_members, 1)
    threshold_count = max(1, int(max_size * threshold_pct / 100))

    current_pct = int(committed_count / max(total_members, 1) * 100) if total_members > 0 else 0
    threshold_met = committed_count >= threshold_count
    amount_target = (trip.estimated_cost_per_person or 0) * max_size

    return {
        "total_members": total_members,
        "committed_count": committed_count,
        "paid_count": paid_count,
        "declined_count": declined_count,
        "pending_count": pending_count,
        "threshold_pct": threshold_pct,
        "current_pct": current_pct,
        "threshold_met": threshold_met,
        "amount_collected": amount_collected,
        "amount_target": amount_target,
    }


__all__ = [
    "transition_trip",
    "check_and_activate",
    "get_commitment_progress",
    "InvalidTransitionError",
    "update_karma",
]
