"""
Rally Group Service — Trip & Swarm Lifecycle Module Alias.
"""

from app.services.swarm_lifecycle import (
    transition_swarm as transition_trip,
    check_and_activate,
    get_commitment_progress,
    InvalidTransitionError,
    update_karma
)

__all__ = [
    "transition_trip",
    "check_and_activate",
    "get_commitment_progress",
    "InvalidTransitionError",
    "update_karma",
]
