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
