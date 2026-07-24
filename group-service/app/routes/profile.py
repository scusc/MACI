from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from maci_core.schemas.profile import PsychometricQuizSubmit, PsychometricProfileResponse
from app.services import matchmaker
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token

router = APIRouter(prefix="/profile", tags=["Psychometric Profile"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/quiz", response_model=PsychometricProfileResponse)
async def submit_quiz(
    quiz: PsychometricQuizSubmit,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit the gamified onboarding quiz. This securely stores the traits, 
    generates a Gemini text-embedding, and saves it to pgvector.
    """
    profile = await matchmaker.process_onboarding_quiz(db, user_id, quiz)
    return PsychometricProfileResponse(
        social_battery=profile.social_battery,
        budget_tolerance=profile.budget_tolerance,
        pacing=profile.pacing,
        spontaneity=profile.spontaneity,
        conflict_style=profile.conflict_style,
        structured_bio=profile.structured_bio,
        profile_completeness_score=profile.profile_completeness_score
    )

@router.get("/me", response_model=PsychometricProfileResponse)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the current user's psychometric profile."""
    from sqlalchemy import select
    from maci_core.models.user import PsychometricProfile
    import uuid
    
    stmt = select(PsychometricProfile).where(PsychometricProfile.user_id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Psychometric profile not found.")
        
    return PsychometricProfileResponse(
        social_battery=profile.social_battery,
        budget_tolerance=profile.budget_tolerance,
        pacing=profile.pacing,
        spontaneity=profile.spontaneity,
        conflict_style=profile.conflict_style,
        structured_bio=profile.structured_bio,
        profile_completeness_score=profile.profile_completeness_score
    )

@router.get("/matches")
async def get_matches(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 5
):
    """
    Agentic Matchmaker: Returns the most psychologically compatible travelers
    in the database using pgvector cosine distance.
    """
    matches = await matchmaker.find_compatible_travelers(db, user_id, limit)
    return {"matches": matches}
