import uuid
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from maci_core.database import get_db
from app.services import vendor_service

router = APIRouter(prefix="/vendor", tags=["Vendor Analytics"])

@router.get("/{host_id}/analytics")
async def get_vendor_analytics(
    host_id: str,
    x_user_id: str = Header(..., description="Simulated authenticated user ID (Host)"),
    db: AsyncSession = Depends(get_db)
):
    """
    B2B Vendor Dashboard Analytics.
    Returns occupancy rates, total revenue, and pool counts for a host.
    """
    # Enforce auth
    if host_id != x_user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Unauthorized. You can only view your own analytics.")
        
    return await vendor_service.get_analytics(db, uuid.UUID(host_id))

from maci_core.models.pool import Pool
from sqlalchemy import select

@router.get("/leads/wholesale")
async def get_wholesale_leads(
    x_user_id: str = Header(..., description="Simulated authenticated Co-Living Operator ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 7: B2B Hospitality Lead Generation API.
    Aggregates 'pods' (Groups that successfully funded a trip) and packages 
    them into anonymous, wholesale leads that Co-living operators can bid on.
    """
    # Find all confirmed pools
    stmt = select(Pool).where(Pool.status == "confirmed")
    pools = (await db.execute(stmt)).scalars().all()
    
    leads = []
    for pool in pools:
        leads.append({
            "lead_id": f"LEAD-{str(pool.id)[:8]}",
            "pod_size": pool.target_slices,
            "destination_asset_id": str(pool.asset_id),
            "estimated_value_cents": pool.target_slices * 50000, # Mock 500/slice value
            "status": "ready_for_bid",
            "anonymized": True
        })
        
    return {
        "operator_id": x_user_id,
        "available_wholesale_leads": len(leads),
        "leads": leads
    }
