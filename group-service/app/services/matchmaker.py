import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from maci_core.models.user import User, PsychometricProfile
from maci_core.schemas.profile import PsychometricQuizSubmit
from maci_core.config import settings
import uuid

# Configure Gemini for Text Embeddings
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_psychometric_embedding(quiz: PsychometricQuizSubmit) -> list[float]:
    """
    Serializes the quiz answers into a psychological narrative and 
    calls Google Gemini to generate a 768-dimensional text embedding vector.
    """
    narrative = f"""
    Traveler Psychometric Profile:
    Social Battery (1-10): {quiz.social_battery}
    Budget Tolerance (1-10): {quiz.budget_tolerance}
    Pacing (1-10): {quiz.pacing}
    Spontaneity (1-10): {quiz.spontaneity}
    Conflict Resolution Style (1-10): {quiz.conflict_style}
    
    Travel Ethos: {quiz.travel_ethos}
    Dealbreakers: {quiz.dealbreakers}
    """
    
    if not settings.GEMINI_API_KEY:
        # Mock embedding for local development without API keys
        return [0.1] * 768
        
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=narrative,
        task_type="clustering"
    )
    return result['embedding']

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
    
    # Calculate profile completeness (assume 100% since they finished the quiz)
    profile.profile_completeness_score = 100.0
    
    await db.commit()
    return profile

async def find_compatible_travelers(db: AsyncSession, user_id: str, limit: int = 5) -> list[dict]:
    """
    Agentic Matchmaker: Uses pgvector cosine distance (<=>) to find the nearest
    neighbors in the psychometric latent space, factoring in completeness.
    """
    # Get current user's profile
    stmt = select(PsychometricProfile).where(PsychometricProfile.user_id == uuid.UUID(user_id))
    result = await db.execute(stmt)
    user_profile = result.scalar_one_or_none()
    
    if not user_profile or not user_profile.embedding:
        return []
        
    # pgvector Cosine Distance query using SQLAlchemy text()
    # We prioritize low distance AND high profile_completeness_score
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
    model = genai.GenerativeModel("gemini-2.0-flash") if settings.GEMINI_API_KEY else None
    
    for row in result:
        compatibility_score = round((1.0 - float(row.distance)) * 100, 2)
        report = "Compatibility report unavailable."
        
        if model:
            try:
                prompt = f"""
                You are an expert travel matchmaker. You have matched two users with a {compatibility_score}% psychological similarity.
                User A (Target): Battery {user_profile.social_battery}/10, Budget {user_profile.budget_tolerance}/10, Pace {user_profile.pacing}/10, Spontaneity {user_profile.spontaneity}/10.
                User B (Matched): Battery {row.social_battery}/10, Budget {row.budget_tolerance}/10, Pace {row.pacing}/10, Spontaneity {row.spontaneity}/10.
                Write exactly 2 sentences explaining why they would make a great travel pod based on their pacing and style. Use an engaging, assuring tone.
                """
                resp = model.generate_content(prompt)
                report = resp.text.strip()
            except Exception as e:
                pass # Fallback to unavailable
                
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
