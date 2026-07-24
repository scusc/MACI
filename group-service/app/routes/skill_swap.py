"""
Skill Swap API Routes — Pod Barter Economy in Rally.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from maci_core.models.skill_swap import PodSkill, SkillSwapRequest, SwapStatus
from maci_core.schemas.skill_swap import (
    PodSkillCreate, PodSkillResponse,
    SkillSwapRequestCreate, SkillSwapRequestResponse
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.core.security import verify_token

router = APIRouter(prefix="/trips", tags=["Pod Skill Swapping"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/{trip_id}/skills", response_model=PodSkillResponse, status_code=status.HTTP_201_CREATED)
async def add_pod_skill(
    trip_id: uuid.UUID,
    body: PodSkillCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a traveler's skill (e.g. Drone Photography, Local Language) to offer inside a trip pod.
    """
    skill = PodSkill(
        trip_id=trip_id,
        user_id=uuid.UUID(user_id),
        category=body.category,
        title=body.title,
        description=body.description,
        estimated_value_cents=body.estimated_value_cents
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return skill


@router.get("/{trip_id}/skills", response_model=List[PodSkillResponse])
async def list_pod_skills(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all skills offered by pod members for a specific trip.
    """
    stmt = select(PodSkill).where(PodSkill.trip_id == trip_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{trip_id}/skills/swap", response_model=SkillSwapRequestResponse, status_code=status.HTTP_201_CREATED)
async def propose_skill_swap(
    trip_id: uuid.UUID,
    body: SkillSwapRequestCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Proposes a skill swap / barter request to offset cost in exchange for a skill contribution.
    """
    # Verify skill exists
    stmt = select(PodSkill).where(PodSkill.id == body.skill_id)
    skill = (await db.execute(stmt)).scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    swap = SkillSwapRequest(
        trip_id=trip_id,
        skill_id=body.skill_id,
        offered_by_user_id=uuid.UUID(user_id),
        target_user_id=body.target_user_id,
        offset_amount_cents=body.offset_amount_cents,
        note=body.note,
        status=SwapStatus.proposed
    )
    db.add(swap)
    await db.commit()
    await db.refresh(swap)
    return swap


@router.post("/skills/swap/{swap_id}/respond", response_model=SkillSwapRequestResponse)
async def respond_skill_swap(
    swap_id: uuid.UUID,
    accept: bool,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts or declines a proposed skill swap.
    """
    stmt = select(SkillSwapRequest).where(SkillSwapRequest.id == swap_id)
    swap = (await db.execute(stmt)).scalar_one_or_none()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")

    swap.status = SwapStatus.accepted if accept else SwapStatus.declined
    await db.commit()
    await db.refresh(swap)
    return swap
