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
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember
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

import httpx
from maci_core.config import settings

async def confirm_pool(db: AsyncSession, pool_id: uuid.UUID) -> dict:
    """
    State Machine: locked -> confirmed.
    The Vibe Check window has closed successfully. 
    Triggers payment-service to CAPTURE all escrow holds and pay the vendor.
    """
    stmt = select(Pool).where(Pool.id == pool_id)
    pool = (await db.execute(stmt)).scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
        
    if pool.status != "locked":
        raise HTTPException(status_code=400, detail="Pool must be in 'locked' state to confirm")
        
    # Trigger Payment Service Escrow Release
    async with httpx.AsyncClient() as client:
        # Assumes payment-service exposes this endpoint locally in the cluster
        # e.g., http://payment-service:8000/api/v1/payments/{pool_id}/release-escrow
        url = f"{settings.payment_service_url}/api/v1/payments/{pool.id}/release-escrow"
        try:
            resp = await client.post(url)
            resp.raise_for_status()
        except Exception as e:
            # If capture fails, we don't transition the state, allowing for manual retry
            raise HTTPException(status_code=500, detail=f"Payment capture failed: {e}")
            
    # Transition State
    pool.status = "confirmed"
    await db.commit()
    
    return {"status": "confirmed", "message": "Escrow captured and vendor paid."}


async def fail_pool(db: AsyncSession, pool_id: uuid.UUID) -> dict:
    """
    State Machine: funding/locked -> failed.
    The trip failed to fund, or collapsed during the Vibe Check window.
    Triggers payment-service to REFUND/CANCEL all escrow authorizations.
    """
    stmt = select(Pool).where(Pool.id == pool_id)
    pool = (await db.execute(stmt)).scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
        
    if pool.status in ["confirmed", "completed"]:
        raise HTTPException(status_code=400, detail="Cannot fail a confirmed pool")
        
    # Trigger Payment Service Refund All
    async with httpx.AsyncClient() as client:
        url = f"{settings.payment_service_url}/api/v1/payments/{pool.id}/refund-all"
        try:
            resp = await client.post(url)
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Payment refund failed: {e}")
            
    # Transition State
    pool.status = "failed"
    await db.commit()
    
    return {"status": "failed", "message": "All escrow authorizations cancelled."}

async def join_pool(db: AsyncSession, pool_id: uuid.UUID, user_id: uuid.UUID, offered_skill: str | None) -> dict:
    """
    Skill-Swapping (Join): User requests to join a pool, optionally offering a skill for a discount.
    They are placed in 'pending_approval' state.
    """
    stmt = select(Pool).where(Pool.id == pool_id)
    pool = (await db.execute(stmt)).scalar_one_or_none()
    
    if not pool or pool.status != "funding":
        raise HTTPException(status_code=400, detail="Pool not available for joining.")
        
    member = PoolMember(
        pool_id=pool_id,
        user_id=user_id,
        offered_skill=offered_skill,
        status="pending_approval"
    )
    db.add(member)
    await db.commit()
    
    return {"status": "pending_approval", "message": f"Requested to join. Offered skill: {offered_skill}"}

async def approve_member(db: AsyncSession, pool_id: uuid.UUID, host_id: uuid.UUID, member_id: uuid.UUID, discount_cents: int) -> dict:
    """
    Skill-Swapping (Approve): Host approves a pending member and grants a discount.
    This triggers the payment-service to pre-authorize the member's card for the discounted price.
    """
    # Verify Host
    stmt = select(Pool).where(Pool.id == pool_id)
    pool = (await db.execute(stmt)).scalar_one_or_none()
    
    if not pool or pool.host_id != host_id:
        raise HTTPException(status_code=403, detail="Only the host can approve members.")
        
    # Verify Member
    m_stmt = select(PoolMember).where(PoolMember.id == member_id, PoolMember.pool_id == pool_id)
    member = (await db.execute(m_stmt)).scalar_one_or_none()
    
    if not member or member.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Member is not pending approval.")
        
    member.discount_cents = discount_cents
    member.status = "approved"
    
    # Trigger Payment-Service Pre-authorization
    # Normally, full_price is calculated from the asset's total price / total slices
    full_price_cents = 50000 # Mocking $500 per slice
    final_amount_cents = max(0, full_price_cents - discount_cents)
    
    async with httpx.AsyncClient() as client:
        url = f"{settings.payment_service_url}/api/v1/payments/create"
        payload = {
            "pool_id": str(pool_id),
            "member_id": str(member.user_id),
            "amount": final_amount_cents,
            "currency": "usd",
            "gateway": "stripe",
            "payment_type": "pool_slice"
        }
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to authorize payment: {e}")
            
    await db.commit()
    return {"status": "approved", "discount_applied": discount_cents, "final_amount": final_amount_cents}
