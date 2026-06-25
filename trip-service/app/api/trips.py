"""
Trip API Routes.

Handles trip CRUD and lifecycle transitions for authenticated org admins.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from maci_core.dependencies import get_current_org_id
from maci_core.database import get_db
from maci_core.schemas.trip import (
    TripCreateRequest,
    TripListResponse,
    TripResponse,
    TripUpdateRequest,
)
from app.services import trip_service

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("", response_model=TripResponse, status_code=201)
async def create_trip(
    request: TripCreateRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new group trip."""
    return await trip_service.create_trip(db, org_id, request)


@router.get("", response_model=TripListResponse)
async def list_trips(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """List all trips for the current organization."""
    return await trip_service.list_trips(db, org_id, offset=offset, limit=limit)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific trip."""
    return await trip_service.get_trip(db, trip_id, org_id)


@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: uuid.UUID,
    request: TripUpdateRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a trip. Only allowed in DRAFT or INTAKE_OPEN state."""
    return await trip_service.update_trip(db, trip_id, org_id, request)


@router.post("/{trip_id}/open-intake", response_model=TripResponse)
async def open_intake(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Open the intake period — generates the shareable link for travelers."""
    return await trip_service.open_intake(db, trip_id, org_id)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a trip. Only allowed in DRAFT state."""
    await trip_service.delete_trip(db, trip_id, org_id)
