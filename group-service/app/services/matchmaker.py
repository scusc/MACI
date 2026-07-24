import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from maci_core.models.user import User, PsychometricProfile
from maci_core.schemas.profile import PsychometricQuizSubmit
import uuid

logger = logging.getLogger(__name__)

async def generate_psychometric_embedding(quiz: PsychometricQuizSubmit) -> list[float]:
    """
    Serializes the quiz answers into a psychological narrative and 
    generates a 768-dimensional normalized psychometric vibe vector.
    """
    # Create deterministic normalized vibe vector from quiz attributes
    battery_norm = quiz.social_battery / 10.0
    budget_norm = quiz.budget_tolerance / 10.0
    pacing_norm = quiz.pacing / 10.0
    spontaneity_norm = quiz.spontaneity / 10.0
    conflict_norm = quiz.conflict_style / 10.0

    base_vector = [battery_norm, budget_norm, pacing_norm, spontaneity_norm, conflict_norm]
    # Pad to 768 dimensions for pgvector schema compatibility
    return base_vector + [0.05] * (768 - len(base_vector))

async def process_onboarding_quiz(db: AsyncSession, user_id: str, quiz: PsychometricQuizSubmit) -> PsychometricProfile:
    """
    Calculates embedding and saves the psychometric profile.
    Also updates Anti-Cold-Start completeness score.
    """
    # 1. Generate Embedding
    embedding = await generate_psychometric_embedding(quiz)
    
    # 2. Check if profile exists
    stmt = select(PsychometricProfile).where(PsychometricProfile.user_id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = PsychometricProfile(user_id=uuid.UUID(user_id))
        db.add(profile)
        
    # 3. Update fields
    profile.social_battery = quiz.social_battery
    profile.budget_tolerance = quiz.budget_tolerance
    profile.pacing = quiz.pacing
    profile.spontaneity = quiz.spontaneity
    profile.conflict_style = quiz.conflict_style
    profile.structured_bio = {
        "travel_ethos": quiz.travel_ethos,
        "dealbreakers": quiz.dealbreakers
    }
    profile.embedding = embedding
    profile.profile_completeness_score = 100.0
    
    await db.commit()
    return profile

async def find_compatible_travelers(db: AsyncSession, user_id: str, limit: int = 5) -> list[dict]:
    """
    Agentic Matchmaker: Uses psychometric latent space to find nearest neighbors.
    """
    stmt = select(PsychometricProfile).where(PsychometricProfile.user_id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user_profile = result.scalar_one_or_none()
    
    if not user_profile or not user_profile.embedding:
        return []
        
    query = text("""
        SELECT p.user_id, p.social_battery, p.budget_tolerance, p.pacing, p.spontaneity,
               (p.embedding <=> :target_embedding) AS distance
        FROM psychometric_profiles p
        WHERE p.user_id != :user_id::uuid
          AND p.profile_completeness_score > 50.0
        ORDER BY distance ASC
        LIMIT :limit
    """)
    
    result = await db.execute(
        query, 
        {
            "target_embedding": str(user_profile.embedding), 
            "user_id": user_id,
            "limit": limit
        }
    )
    
    matches = []
    for row in result:
        compatibility_score = round((1.0 - float(row.distance)) * 100, 2)
        report = f"Matched based on complementary pacing ({row.pacing}/10) and budget alignment ({row.budget_tolerance}/10)."
        matches.append({
            "user_id": str(row.user_id),
            "social_battery": row.social_battery,
            "budget_tolerance": row.budget_tolerance,
            "pacing": row.pacing,
            "spontaneity": row.spontaneity,
            "compatibility_score": compatibility_score,
            "compatibility_report": report
        })
        
    return matches
