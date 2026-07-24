"""
Psychometric AI Matching API Routes — Rally.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import uuid

from maci_core.database import get_db
from app.services.matching_service import find_psychometric_matches
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token

router = APIRouter(prefix="/matching", tags=["Psychometric Matching"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/recommendations", response_model=List[Dict[str, Any]])
async def get_psychometric_recommendations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns top compatible co-traveler recommendations using 5D psychometric compatibility
    and Zero-Knowledge shielded avatar profiles.
    """
    return await find_psychometric_matches(uuid.UUID(user_id), db)
