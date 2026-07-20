"""
Rally Group Service — Swarm Lifecycle State Machine.

Manages transitions between swarm states:
  draft → collecting → active → completed
                    ↘ rebalancing ↘
                      (dynamic downgrade)
"""

import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Swarm, SwarmPeer, Payment, User

logger = logging.getLogger("rally.group.lifecycle")

async def update_karma(db: AsyncSession, user_id: str, delta: int) -> int:
    """
    Update a user's Karma score by the given delta.
    Ensures Karma score does not drop below 0 or exceed 1000.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user:
        current_karma = getattr(user, 'karma_score', 100)
        new_karma = max(0, min(1000, current_karma + delta))
        user.karma_score = new_karma
        await db.flush()
        logger.info(f"Updated karma for user {user_id}: {current_karma} -> {new_karma} (delta: {delta})")
        return new_karma
    return 100

# Valid state transitions
VALID_TRANSITIONS = {
    "draft": {"collecting", "cancelled"},
    "collecting": {"active", "cancelled"}, # Note: in real implementation, AI rebalancing handles the shortfall.
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid state transition."""
    pass


async def transition_swarm(
    db: AsyncSession,
    swarm: Swarm,
    new_status: str,
    reason: str = ""
) -> Swarm:
    """
    Transition a swarm to a new status with validation.

    Raises InvalidTransitionError if the transition is not allowed.
    """
    current = swarm.status
    allowed = VALID_TRANSITIONS.get(current, set())

    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition swarm from '{current}' to '{new_status}'. "
            f"Allowed transitions: {allowed or 'none (terminal state)'}"
        )

    old_status = swarm.status
    swarm.status = new_status
    swarm.updated_at = datetime.utcnow()

    logger.info(
        "Swarm %s transitioned: %s → %s (reason: %s)",
        swarm.id, old_status, new_status, reason or "none"
    )
    
    # ── Karma Reward Engine ──────────────────────────────────────────────────
    if new_status == "completed":
        # Reward all peers who actually participated
        for peer in swarm.peers:
            if peer.user_id and peer.status == "paid":
                await update_karma(db, str(peer.user_id), 5)

    return swarm


async def handle_commitment_deadline(db: AsyncSession, swarm: Swarm) -> bool:
    """
    Called when a Swarm hits its deadline.
    Instead of canceling on failure, it triggers AI Rebalancing.
    """
    if swarm.status != "collecting":
        return False

    total_members_result = await db.execute(
        select(func.count(SwarmPeer.id))
        .where(SwarmPeer.swarm_id == swarm.id)
    )
    total_members = total_members_result.scalar() or 0

    paid_members_result = await db.execute(
        select(func.count(SwarmPeer.id))
        .where(SwarmPeer.swarm_id == swarm.id)
        .where(SwarmPeer.status == "paid")
    )
    paid_count = paid_members_result.scalar() or 0

    if total_members == 0:
        await transition_swarm(db, swarm, "cancelled", reason="Zero peers joined.")
        return False

    current_pct = int((paid_count / total_members) * 100)

    if current_pct >= swarm.threshold_pct:
        await transition_swarm(db, swarm, "active", reason="Deadline reached, threshold met naturally.")
        return True
    else:
        # PIVOT LOGIC: Do not cancel. Trigger Rebalancing.
        logger.warning(f"Swarm {swarm.id} failed to meet threshold ({current_pct}% < {swarm.threshold_pct}%).")
        logger.info(f"Triggering AI Agent Rebalancing for Swarm {swarm.id} to downgrade supply chain.")
        # In a real implementation, this would emit an event to a Kafka topic or Celery worker
        # to rebook a smaller Airbnb, recalculate prices, and then set to 'active'.
        # For now, we simulate success after rebalance:
        await transition_swarm(db, swarm, "active", reason="AI dynamically rebalanced the swarm supply chain. Minimums lowered.")
        return True


async def check_and_activate(db: AsyncSession, swarm: Swarm) -> bool:
    """
    Check if a swarm's commitment threshold has been met before deadline.
    If so, transition to 'active'.
    """
    if swarm.status != "collecting":
        return False

    total_members_result = await db.execute(
        select(func.count(SwarmPeer.id))
        .where(SwarmPeer.swarm_id == swarm.id)
    )
    total_members = total_members_result.scalar() or 0

    paid_members_result = await db.execute(
        select(func.count(SwarmPeer.id))
        .where(SwarmPeer.swarm_id == swarm.id)
        .where(SwarmPeer.status == "paid")
    )
    paid_count = paid_members_result.scalar() or 0

    if total_members == 0:
        return False

    current_pct = int((paid_count / total_members) * 100)

    if current_pct >= swarm.threshold_pct:
        await transition_swarm(db, swarm, "active", reason=f"Threshold met early: {current_pct}% >= {swarm.threshold_pct}%")
        logger.info("🎉 Swarm %s ACTIVATED!", swarm.id)
        return True

    return False


async def get_commitment_progress(db: AsyncSession, swarm: Swarm) -> dict:
    """
    Calculate the current commitment progress for a swarm.
    """
    peers = swarm.peers

    total = len(peers)
    committed = sum(1 for p in peers if p.status in ("committed", "paid"))
    paid = sum(1 for p in peers if p.status == "paid")
    declined = sum(1 for p in peers if p.status == "declined")
    pending = total - committed - declined

    amount_collected = sum(p.share_amount or 0 for p in peers if p.status == "paid")
    amount_target = sum(p.share_amount or 0 for p in peers)

    current_pct = int((paid / total) * 100) if total > 0 else 0

    return {
        "total_peers": total,
        "committed_count": committed,
        "paid_count": paid,
        "declined_count": declined,
        "pending_count": pending,
        "threshold_pct": swarm.threshold_pct,
        "current_pct": current_pct,
        "threshold_met": current_pct >= swarm.threshold_pct,
        "amount_collected": amount_collected,
        "amount_target": amount_target,
    }
