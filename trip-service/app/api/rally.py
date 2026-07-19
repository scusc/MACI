"""
Rally Integration Routes.

These endpoints expose the AI planning capabilities to the Rally Group Service.
"""

from fastapi import APIRouter, HTTPException
from maci_core.schemas.rally import (
    CostEstimateRequest, CostEstimateResponse, OriginCostBreakdown,
    TripPlanRequest, TripPlanResponse, TripCreate
)
from app.services.orchestrator import build_orchestrator_graph
from maci_core.schemas.ai import GroupItinerary

router = APIRouter(prefix="/api/v1", tags=["Rally AI"])


@router.post("/estimate", response_model=CostEstimateResponse)
async def get_cost_estimate(req: CostEstimateRequest):
    """
    Generate an AI cost estimate for a group trip.
    This replaces the "Plan My Trip" orchestrator for the Pre-Commitment phase.
    """
    # In a real implementation, this would call the SerpAPI flight/hotel tools
    # to get real-time price estimates based on the origins and destination.
    # For now, we return a mock response that scales with travelers.

    flight_estimates = []
    total_flight_cost = 0

    for origin in req.origins:
        # Mock logic: if origin starts with 'S' or 'J' it's more expensive
        cost = 45000 if origin[0] in ('S', 'J') else 32000
        total_flight_cost += cost
        flight_estimates.append(
            OriginCostBreakdown(
                origin_airport=origin,
                estimated_flight_cost=cost,
                price_level="typical",
                confidence="estimate"
            )
        )

    avg_flight_cost = total_flight_cost // len(req.origins) if req.origins else 0
    hotel_per_night = 7500  # $75 per person per night

    # Assume 4 nights for the total estimate
    nights = 4
    if req.end_date:
        nights = (req.end_date - req.start_date).days or 4

    total_per_person = avg_flight_cost + (hotel_per_night * nights)

    return CostEstimateResponse(
        destination=req.destination,
        flight_estimates=flight_estimates,
        estimated_hotel_per_night=hotel_per_night,
        estimated_total_per_person=total_per_person,
        price_trend="stable",
        recommendation="Prices are stable. Lock in now to ensure group alignment."
    )


@router.post("/plan", response_model=TripPlanResponse)
async def plan_group_trip(req: TripPlanRequest):
    """
    Execute the full Multi-Agent LangGraph workflow to generate a structured
    trip itinerary and the corresponding payload to initialize a Rally trip.
    """
    # 1. Prepare LangGraph state
    travelers_state = [
        {
            "traveler_id": f"t_{i}",
            "origin_airport": t.origin_airport,
            "earliest_departure": "06:00",
            "latest_arrival": "23:59",
            "budget_flights_usd": t.budget_flights_usd
        }
        for i, t in enumerate(req.travelers)
    ]
    
    initial_state = {
        "destination": req.destination,
        "outbound_date": req.start_date.isoformat(),
        "return_date": req.end_date.isoformat(),
        "travelers": travelers_state
    }

    # 2. Execute Orchestrator Graph
    graph = build_orchestrator_graph()
    # Note: In production with long execution times, we'd use a background task / Celery / Azure Service Bus.
    # For this MVP, we block synchronously.
    result_state = await graph.ainvoke(initial_state)

    # 3. Process outputs
    converged = result_state.get("converged_itinerary")
    if not converged or not converged.is_successful:
        raise HTTPException(
            status_code=422,
            detail=f"AI could not converge on a valid trip: {converged.failure_reason if converged else 'Unknown error'}"
        )
    
    # Calculate costs
    avg_flight_cost = (converged.total_group_flight_cost / len(req.travelers)) if req.travelers else 0
    # Add mock hotel cost for estimation since Phase 6 is pending
    hotel_cost_per_person = 300 * 100 # $300 for the trip
    
    estimated_cost_cents = int(avg_flight_cost + hotel_cost_per_person)
    
    # 4. Generate Rally Payload
    rally_payload = TripCreate(
        title=f"Group Trip to {req.destination}",
        destination=req.destination,
        start_date=req.start_date,
        end_date=req.end_date,
        description=result_state.get("price_intelligence", "An amazing group trip!"),
        currency="USD",
        threshold_pct=80,
        estimated_cost_per_person=estimated_cost_cents,
        commitment_deadline=None
    )
    
    ai_itinerary = GroupItinerary(
        destination=req.destination,
        outbound_date=req.start_date.isoformat(),
        return_date=req.end_date.isoformat(),
        convergence=converged,
        hotel_allocations=result_state.get("hotels", []),
        activities=result_state.get("activities", []),
        price_intelligence=result_state.get("price_intelligence", "")
    )

    return TripPlanResponse(
        rally_trip_payload=rally_payload,
        ai_itinerary=ai_itinerary
    )
