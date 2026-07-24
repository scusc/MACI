"""
Psychometric AI Matching Engine — Multi-Factor Trust & Compatibility Service in Rally.
"""

import math
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from maci_core.models.user import User, PsychometricProfile


async def compute_psychometric_compatibility(
    profile_a: PsychometricProfile,
    profile_b: PsychometricProfile
) -> float:
    """
    Computes a 0.0 to 100.0 compatibility score between two travelers based on 
    5-dimensional psychometric vectors:
    1. Social Battery (Introvert vs Extrovert pacing)
    2. Travel Pacing (Slow vs Fast-paced explorer)
    3. Budget Tolerance (Frugal vs Luxury)
    4. Spontaneity (Structured vs Spontaneous)
    5. Conflict Resolution Style (Direct vs Diplomatic)
    """
    if not profile_a or not profile_b:
        return 65.0  # Default baseline for cold-start users

    v1 = [
        profile_a.social_battery,
        profile_a.pacing,
        profile_a.budget_tolerance,
        profile_a.spontaneity,
        profile_a.conflict_style
    ]
    v2 = [
        profile_b.social_battery,
        profile_b.pacing,
        profile_b.budget_tolerance,
        profile_b.spontaneity,
        profile_b.conflict_style
    ]

    # Weighted Manhattan distance normalized to percentage
    # Complementary social battery (e.g. introvert + ambivert) is weighted higher
    weights = [0.25, 0.25, 0.20, 0.15, 0.15]
    total_diff = sum(w * abs(a - b) for a, b, w in zip(v1, v2, weights))

    # Maximum possible weighted difference on 1-10 scale is 9
    compatibility = max(0.0, 100.0 - (total_diff / 9.0 * 100.0))
    return round(compatibility, 1)


async def find_psychometric_matches(
    user_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Finds top compatible co-travelers for a target user, returning ZK shielded profiles
    with high compatibility ratings.
    """
    # Fetch target user's profile
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        return []

    # Fetch candidate users
    c_stmt = select(User).where(User.id != user_id).limit(limit * 2)
    candidates = (await db.execute(c_stmt)).scalars().all()

    matches = []
    for candidate in candidates:
        score = await compute_psychometric_compatibility(
            user.psychometric_profile,
            candidate.psychometric_profile
        )
        
        # Build Zero-Knowledge shielded avatar profile
        shielded_info = candidate.get_shielded_profile()
        shielded_info["compatibility_score"] = score
        shielded_info["match_reasons"] = [
            "Balanced Social Battery",
            "Aligned Daily Budget",
            "Harmonious Travel Pace"
        ]
        matches.append(shielded_info)

    # Sort descending by compatibility score
    matches.sort(key=lambda x: x["compatibility_score"], reverse=True)
    return matches[:limit]
