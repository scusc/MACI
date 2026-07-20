"""
Asset & Pool Service.
Handles importing assets and managing pools.
"""

from typing import List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from maci_core.models.asset import Asset
from maci_core.models.pool import Pool, PoolMember
from maci_core.models.user import User
from maci_core.schemas.asset import AssetCreate, AssetResponse
from maci_core.schemas.pool import PoolCreate, PoolResponse


async def import_assets(db: AsyncSession, assets: List[AssetCreate]) -> List[AssetResponse]:
    """Import mock assets into the database."""
    created_assets = []
    for asset_data in assets:
        asset = Asset(**asset_data.model_dump())
        db.add(asset)
        created_assets.append(asset)
    
    await db.commit()
    for a in created_assets:
        await db.refresh(a)
        
    return [AssetResponse.model_validate(a) for a in created_assets]


async def create_pool(db: AsyncSession, host_id: uuid.UUID, pool_data: PoolCreate) -> PoolResponse:
    """Create a new pool for an asset and automatically add the host as a member."""
    # Ensure asset exists
    stmt = select(Asset).where(Asset.id == pool_data.asset_id)
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    pool = Pool(
        asset_id=pool_data.asset_id,
        host_id=host_id,
        start_date=pool_data.start_date,
        end_date=pool_data.end_date,
        funding_deadline=pool_data.funding_deadline,
        status="funding"
    )
    db.add(pool)
    await db.flush()

    # Add host as a committed member
    host_member = PoolMember(
        pool_id=pool.id,
        user_id=host_id,
        slices_committed=1,
        status="approved" # Host is automatically approved
    )
    db.add(host_member)
    await db.commit()
    await db.refresh(pool)
    
    return PoolResponse.model_validate(pool)


async def get_swipe_feed(db: AsyncSession, user_id: uuid.UUID) -> List[PoolResponse]:
    """
    Matchmaking / Swipe Query Logic.
    Find open/funding pools where the user's karma score meets requirements.
    (Simplified mock logic for Phase 4)
    """
    stmt = select(Pool).where(Pool.status == "funding").where(Pool.host_id != user_id)
    result = await db.execute(stmt)
    pools = result.scalars().all()
    
    # In a real app, we would filter by the host's required Karma, dates, etc.
    return [PoolResponse.model_validate(p) for p in pools]
