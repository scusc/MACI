import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember
from maci_core.models.asset import Asset

async def get_analytics(db: AsyncSession, host_id: uuid.UUID) -> dict:
    """
    Computes Host / Vendor analytics:
    - Total pools created
    - Total successful revenue (Pools that are 'confirmed' or 'completed')
    - Occupancy rate (Total slices filled / Total slices available)
    """
    
    # Total Pools Created
    pool_stmt = select(func.count(Pool.id)).where(Pool.host_id == host_id)
    total_pools = (await db.execute(pool_stmt)).scalar() or 0
    
    # Active Escrows (Funding / Locked)
    active_stmt = select(func.count(Pool.id)).where(
        Pool.host_id == host_id, 
        Pool.status.in_(["funding", "locked"])
    )
    active_escrows = (await db.execute(active_stmt)).scalar() or 0
    
    # Fetch all confirmed/completed pools for revenue calculation
    confirmed_stmt = select(Pool.id, Asset.price_cents).join(Asset, Pool.asset_id == Asset.id).where(
        Pool.host_id == host_id,
        Pool.status.in_(["confirmed", "completed"])
    )
    confirmed_results = (await db.execute(confirmed_stmt)).all()
    
    total_revenue_cents = 0
    for row in confirmed_results:
        pool_id, price_cents = row
        # In a real app, we'd sum the actual payment authorizations.
        # Here we assume the pool filled its slices at the asset's total price minus 5% platform fee
        platform_fee = int(price_cents * 0.05)
        vendor_cut = price_cents - platform_fee
        total_revenue_cents += vendor_cut
        
    # Occupancy Rate (Slices Committed / Total Capacity)
    # We sum all slices committed across all non-failed pools
    occupancy_rate = 0.0
    if total_pools > 0:
        slices_stmt = select(func.sum(PoolMember.slices_committed)).join(Pool, PoolMember.pool_id == Pool.id).where(
            Pool.host_id == host_id,
            Pool.status != "failed"
        )
        total_slices_filled = (await db.execute(slices_stmt)).scalar() or 0
        
        capacity_stmt = select(func.sum(Asset.total_slices)).join(Pool, Pool.asset_id == Asset.id).where(
            Pool.host_id == host_id,
            Pool.status != "failed"
        )
        total_capacity = (await db.execute(capacity_stmt)).scalar() or 1
        
        if total_capacity > 0:
            occupancy_rate = (total_slices_filled / total_capacity) * 100
            
    return {
        "host_id": str(host_id),
        "total_pools_created": total_pools,
        "active_escrows": active_escrows,
        "total_revenue_cents": total_revenue_cents,
        "occupancy_rate_percentage": round(occupancy_rate, 2)
    }
