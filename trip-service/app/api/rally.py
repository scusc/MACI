"""
Rally Integration Routes.

These endpoints expose the AI planning capabilities to the Rally Group Service.
"""

from fastapi import APIRouter
from maci_core.schemas.rally import CostEstimateRequest, CostEstimateResponse, OriginCostBreakdown

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
