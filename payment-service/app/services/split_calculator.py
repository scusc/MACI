"""
Rally Payment Service — Fee and Split Calculators.
"""

from app.config import settings
from maci_core.schemas.rally import CostEstimateResponse


def calculate_platform_fee(amount_cents: int) -> int:
    """
    Calculate the Rally platform fee.
    Basis points (e.g., 300 bps = 3.0%).
    """
    if amount_cents <= 0:
        return 0
    return int(amount_cents * settings.platform_fee_bps / 10000)


def calculate_splits(cost_estimate: CostEstimateResponse) -> dict[str, int]:
    """
    Calculate per-member splits based on origin-specific flight costs
    and evenly distributed hotel/activity costs.

    Returns a dict mapping origin_airport -> total_cost_in_cents (NOT including fee)
    """
    splits = {}

    # Total shared costs per person
    shared_costs = 0
    if cost_estimate.estimated_hotel_per_night:
        # Assuming 4 nights for now, we'd need actual duration from trip
        # For this prototype, we'll just use a placeholder of 4 nights if not specified
        nights = 4 
        shared_costs += (cost_estimate.estimated_hotel_per_night * nights)

    # Add flight cost per origin
    for breakdown in cost_estimate.flight_estimates:
        origin = breakdown.origin_airport
        flight_cost = breakdown.estimated_flight_cost
        splits[origin] = flight_cost + shared_costs

    return splits
