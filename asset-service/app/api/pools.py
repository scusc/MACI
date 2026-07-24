"""
Pools API Routes.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.database import get_db
from maci_core.schemas.pool import PoolCreate, PoolResponse
from app.services import pool_service

router = APIRouter(prefix="/pools", tags=["Pools"])

@router.post("/", response_model=PoolResponse)
async def create_pool(
    pool_data: PoolCreate,
    x_user_id: str = Header(..., description="Simulated authenticated user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Create a new pool for an asset."""
    host_id = uuid.UUID(x_user_id)
    return await pool_service.create_pool(db, host_id, pool_data)

@router.get("/feed", response_model=List[PoolResponse])
async def get_feed(
    x_user_id: str = Header(..., description="Simulated authenticated user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get the Swipe Feed of available pools."""
    user_id = uuid.UUID(x_user_id)
    return await pool_service.get_swipe_feed(db, user_id)

@router.post("/{pool_id}/confirm")
async def confirm_pool_state(
    pool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Transitions pool to confirmed.
    Triggers payment capture in payment-service.
    """
    return await pool_service.confirm_pool(db, uuid.UUID(pool_id))

@router.post("/{pool_id}/fail")
async def fail_pool_state(
    pool_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Transitions pool to failed.
    Triggers payment refund in payment-service.
    """
    return await pool_service.fail_pool(db, uuid.UUID(pool_id))

from maci_core.schemas.pool import PoolMemberJoin, PoolMemberApprove

@router.post("/{pool_id}/join")
async def join_pool(
    pool_id: str,
    data: PoolMemberJoin,
    x_user_id: str = Header(..., description="Simulated authenticated user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Skill-Swapping: Join a pool and optionally offer a skill for a discount.
    """
    return await pool_service.join_pool(db, uuid.UUID(pool_id), uuid.UUID(x_user_id), data.offered_skill)

@router.post("/{pool_id}/members/{member_id}/approve")
async def approve_member(
    pool_id: str,
    member_id: str,
    data: PoolMemberApprove,
    x_user_id: str = Header(..., description="Simulated authenticated user ID (Host)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Skill-Swapping: Host approves a member and applies a discount.
    Triggers payment-service to authorize the discounted amount.
    """
    return await pool_service.approve_member(
        db=db,
        pool_id=uuid.UUID(pool_id),
        host_id=uuid.UUID(x_user_id),
        member_id=uuid.UUID(member_id),
        discount_cents=data.discount_cents
    )
