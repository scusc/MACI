"""
Price Intelligence & Deals Agent

This agent uses the Price Insights and Flight Deals tools to generate
booking recommendations and surface proactive deal alerts for the group.
"""

from typing import Dict, Any

from app.tools.serp_client import SerpClient
from app.tools.price_intel import create_price_insights_tool, create_flight_deals_tool
from maci_core.schemas.ai import ConvergedItinerary

# In production, we'd use the LLM to write a summary of the pricing.
# For this phase, we'll build a lightweight Python orchestrator that uses the tools directly
# to append price intelligence to the converged itinerary.

def run_price_intelligence(
    destination: str, 
    converged: ConvergedItinerary, 
    mock_mode: bool = True
) -> str:
    """
    Analyzes the selected flights in the converged itinerary and generates
    a price trend recommendation for the group.
    """
    if not converged.is_successful or not converged.selected_flights:
        return "No valid itinerary to analyze."

    client = SerpClient(mock_mode=mock_mode)
    insights_tool = create_price_insights_tool(client)
    
    # Analyze the most expensive route in the group to drive the booking decision
    # (If the most expensive route is currently "High", the group should wait)
    
    most_expensive_flight = max(
        converged.selected_flights, 
        key=lambda f: getattr(f, "total_price_usd", f.get("total_price_usd", 0)) if isinstance(f, dict) else f.total_price_usd
    )
    
    origin = getattr(most_expensive_flight, "origin_airport", most_expensive_flight.get("origin_airport", "UNKNOWN")) if isinstance(most_expensive_flight, dict) else most_expensive_flight.origin_airport
    
    # We would extract the actual date, assuming a fixed date for now based on the first segment
    date = "2026-08-15" 
    
    try:
        # Call the tool directly (without LLM for speed/reliability on this step)
        insights_json = insights_tool.invoke({
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date
        })
        
        import json
        data = json.loads(insights_json)
        
        recommendation = data.get("recommendation", "Pricing data unavailable.")
        price_level = data.get("price_level", "unknown")
        
        report = (
            f"Price Intelligence based on the most expensive route ({origin} → {destination}):\n"
            f"- Current Price Level: {price_level.upper()}\n"
            f"- Recommendation: {recommendation}"
        )
        return report
        
    except Exception as e:
        return f"Price intelligence unavailable: {str(e)}"
