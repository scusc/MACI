"""
Asset API Routes.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.database import get_db
from maci_core.schemas.asset import AssetResponse
from pydantic import BaseModel
from app.services import pool_service, serpapi_client

router = APIRouter(prefix="/assets", tags=["Assets"])

class SerpApiSearchRequest(BaseModel):
    query: str
    check_in: str
    check_out: str
    adults: int = 4
    category: str = "general"

from maci_core.schemas.asset import AssetCreate

@router.post("/", response_model=AssetResponse)
async def create_asset(request: AssetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new asset manually."""
    # Assuming asset_service.create_asset exists or we can just create and add
    from maci_core.models.asset import Asset
    import uuid
    asset = Asset(
        id=uuid.uuid4(),
        title=request.title,
        description=request.description,
        asset_type=request.asset_type,
        category=request.category,
        location=request.location,
        total_price=request.total_price,
        currency=request.currency,
        total_slices=request.total_slices,
    )
    db.add(asset)
    await db.commit()
    return asset

@router.post("/import-from-serpapi", response_model=List[AssetResponse])
async def import_assets_from_serpapi(request: SerpApiSearchRequest, db: AsyncSession = Depends(get_db)):
    """Fetch live inventory from SerpAPI and import into the database."""
    assets = await serpapi_client.search_inventory(
        query=request.query,
        check_in=request.check_in,
        check_out=request.check_out,
        adults=request.adults,
        category=request.category
    )
    return await pool_service.import_assets(db, assets)

class SerpApiEventSearchRequest(BaseModel):
    query: str
    location: str
    category: str = "event"

@router.post("/import-events-from-serpapi", response_model=List[AssetResponse])
async def import_events_from_serpapi(request: SerpApiEventSearchRequest, db: AsyncSession = Depends(get_db)):
    """Fetch live event inventory (Concerts, Festivals) from SerpAPI and import into the database."""
    assets = await serpapi_client.search_events(
        query=request.query,
        location=request.location,
        category=request.category
    )
    return await pool_service.import_assets(db, assets)

from fastapi import HTTPException
import uuid
from maci_core.models.asset import Asset
from sqlalchemy import select
from datetime import datetime

@router.get("/{asset_id}/dynamic-price")
async def get_dynamic_price(asset_id: str, db: AsyncSession = Depends(get_db)):
    """
    Phase 7: AI-Driven Dynamic Pricing Engine.
    Adjusts the matching premium based on demand/seasonality.
    """
    stmt = select(Asset).where(Asset.id == uuid.UUID(asset_id))
    asset = (await db.execute(stmt)).scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    current_month = datetime.now().month
    
    # Simple algorithmic pricing engine mock
    # Summer months (June, July, August) get a 1.2x surge
    # Winter months (Dec, Jan, Feb) get a 0.8x discount
    # Others are 1.0x baseline
    if current_month in [6, 7, 8]:
        multiplier = 1.20
        season = "summer_surge"
    elif current_month in [12, 1, 2]:
        multiplier = 0.80
        season = "winter_discount"
    else:
        multiplier = 1.00
        season = "baseline"
        
    dynamic_price = asset.total_price * multiplier
    
    return {
        "asset_id": str(asset.id),
        "base_price": asset.total_price,
        "dynamic_price": dynamic_price,
        "multiplier": multiplier,
        "season_modifier": season,
        "currency": asset.currency
    }
