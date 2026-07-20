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
