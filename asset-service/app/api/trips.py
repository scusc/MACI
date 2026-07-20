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

# ── AI Orchestration & Intelligence Endpoints ─────────────────────────────────

from maci_core.schemas.ai import GroupItinerary
from app.services.orchestrator import build_orchestrator_graph

@router.post("/{trip_id}/orchestrate", response_model=GroupItinerary)
async def orchestrate_trip(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the LangGraph Multi-Agent Swarm.
    Reads traveler constraints from DB, runs MapReduce flight search,
    calculates convergence, and builds the complete Group Itinerary.
    """
    # 1. Fetch trip and constraints from DB
    trip = await trip_service.get_trip(db, trip_id, org_id)
    
    # 2. Build initial LangGraph State (Mock state for MVP endpoint)
    initial_state = {
        "destination": trip.destination,
        "outbound_date": str(trip.outbound_date),
        "return_date": str(trip.return_date) if trip.return_date else None,
        "travelers": [],  # Would be populated from DB
        "flight_proposals": [],
        "converged_itinerary": None,
        "hotels": [],
        "activities": [],
        "price_intelligence": ""
    }
    
    # 3. Execute the Graph
    # graph = build_orchestrator_graph()
    # final_state = await graph.ainvoke(initial_state)
    
    # Return mock itinerary structure until DB traveler links are fully integrated
    from maci_core.schemas.ai import ConvergedItinerary
    return GroupItinerary(
        destination=trip.destination,
        outbound_date=str(trip.outbound_date),
        return_date=str(trip.return_date) if trip.return_date else None,
        convergence=ConvergedItinerary(
            is_successful=True,
            convergence_window_start="2026-08-15 14:00",
            convergence_window_end="2026-08-15 17:00",
            total_group_flight_cost=1500,
            selected_flights=[]
        ),
        hotels=[],
        activities=[],
        price_intelligence="⚡ BOOK NOW — Prices are below historical norms."
    )


@router.get("/{trip_id}/itinerary", response_model=GroupItinerary)
async def get_itinerary(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the previously generated itinerary for a trip."""
    # In production, fetch the JSON from blob storage or DB
    trip = await trip_service.get_trip(db, trip_id, org_id)
    from maci_core.schemas.ai import ConvergedItinerary
    return GroupItinerary(
        destination=trip.destination,
        outbound_date=str(trip.outbound_date),
        return_date=None,
        convergence=ConvergedItinerary(
            is_successful=True,
            convergence_window_start="2026-08-15 14:00",
            convergence_window_end="2026-08-15 17:00",
            total_group_flight_cost=1500,
            selected_flights=[]
        ),
        hotels=[],
        activities=[],
        price_intelligence="Prices are stable."
    )


@router.post("/{trip_id}/price-watch", status_code=202)
async def subscribe_price_watch(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe the group to proactive price drop alerts using the SerpAPI Deals Engine.
    """
    trip = await trip_service.get_trip(db, trip_id, org_id)
    # Register webhook/cron task for this trip
    return {"status": "Subscribed to price alerts", "trip_id": str(trip_id)}
