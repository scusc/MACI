"""
Tests for Payment Service Calculators.
"""

from app.services.split_calculator import calculate_platform_fee, calculate_splits
from maci_core.schemas.rally import CostEstimateResponse, OriginCostBreakdown

def test_calculate_platform_fee():
    # Base fee is 3.0% (300 bps)
    assert calculate_platform_fee(10000) == 300   # $100 -> $3
    assert calculate_platform_fee(0) == 0
    assert calculate_platform_fee(-50) == 0
    
    # 15450 cents -> 154.50 -> 3% is 463.5 -> 463 cents
    assert calculate_platform_fee(15450) == 463

def test_calculate_splits():
    estimate = CostEstimateResponse(
        destination="BCN",
        flight_estimates=[
            OriginCostBreakdown(origin_airport="JFK", estimated_flight_cost=32000, price_level="typical"),
            OriginCostBreakdown(origin_airport="BOM", estimated_flight_cost=58000, price_level="high")
        ],
        estimated_hotel_per_night=5000, # $50 per person per night
        estimated_total_per_person=0,
        price_trend="stable",
        recommendation=None
    )
    
    splits = calculate_splits(estimate)
    
    # Hotel shared cost: $50 * 4 nights = $200 (20000 cents)
    # JFK flight: $320 (32000 cents) -> Total JFK = 52000 cents
    # BOM flight: $580 (58000 cents) -> Total BOM = 78000 cents
    
    assert "JFK" in splits
    assert "BOM" in splits
    assert splits["JFK"] == 52000
    assert splits["BOM"] == 78000
