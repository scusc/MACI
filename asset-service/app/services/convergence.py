"""
Convergence Algorithm Module

This module implements the deterministic multi-origin convergence logic.
Unlike the Flight Delegates which use LLMs for fuzzy search and reasoning,
the convergence node uses pure Python to find the optimal mathematical
combination of flights that guarantees the group arrives together.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from maci_core.schemas.ai import ConvergedItinerary, FlightProposal

logger = logging.getLogger("maci.convergence")

# The maximum allowed gap between the first person arriving and the last person arriving
MAX_CONVERGENCE_GAP_HOURS = 4


def _parse_time(time_str: str) -> datetime:
    """Helper to parse ISO8601 strings from the LLM/API."""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(time_str[:16], fmt)
        except ValueError:
            continue
    logger.warning(f"Failed to parse time string: {time_str}")
    return datetime.min


def run_convergence_algorithm(proposals_by_origin: List[Dict[str, Any]]) -> ConvergedItinerary:
    """
    Finds the cheapest combination of flights where all travelers arrive
    within MAX_CONVERGENCE_GAP_HOURS of each other.
    
    Args:
        proposals_by_origin: A list of dicts. Each dict has an "origin" 
                             and a "proposals" list of FlightProposal objects.
    """
    # 1. Generate all possible combinations of 1 flight per origin
    import itertools
    
    # proposals_by_origin looks like:
    # [
    #   {"origin": "SFO", "proposals": [FlightProposal, FlightProposal]},
    #   {"origin": "JFK", "proposals": [FlightProposal]}
    # ]
    
    lists_of_proposals = [item.get("proposals", []) for item in proposals_by_origin]
    
    if not lists_of_proposals or not all(lists_of_proposals):
        failed_origins = [
            item.get("origin", "Unknown") 
            for item in proposals_by_origin 
            if not item.get("proposals")
        ]
        return ConvergedItinerary(
            is_successful=False,
            convergence_window_start=None,
            convergence_window_end=None,
            total_group_flight_cost=0,
            selected_flights=[],
            failure_reason=f"The following origins returned no valid flight proposals: {', '.join(failed_origins)}. Their constraints (budget/timing) are likely too strict."
        )

    all_combinations = list(itertools.product(*lists_of_proposals))
    
    valid_combinations = []
    
    # 2. Evaluate each combination
    for combo in all_combinations:
        # combo is a tuple of FlightProposals (one from each origin)
        
        # Get arrival times (from the last segment of each proposal)
        arrival_times = []
        total_cost = 0
        
        for proposal in combo:
            # Check for dict vs object (depending on how Pydantic serialized it in state)
            if isinstance(proposal, dict):
                total_cost += proposal.get("total_price_usd", 0)
                segments = proposal.get("segments", [])
            else:
                total_cost += getattr(proposal, "total_price_usd", 0)
                segments = getattr(proposal, "segments", [])
                
            if segments:
                last_segment = segments[-1]
                arr_time_str = last_segment.get("arrival_time") if isinstance(last_segment, dict) else getattr(last_segment, "arrival_time")
                if arr_time_str:
                    arrival_times.append(_parse_time(arr_time_str))
        
        if not arrival_times or len(arrival_times) != len(combo):
            continue
            
        # Check convergence gap
        earliest_arrival = min(arrival_times)
        latest_arrival = max(arrival_times)
        
        gap = latest_arrival - earliest_arrival
        
        if gap <= timedelta(hours=MAX_CONVERGENCE_GAP_HOURS):
            valid_combinations.append({
                "combo": combo,
                "cost": total_cost,
                "earliest": earliest_arrival,
                "latest": latest_arrival
            })
            
    # 3. Select the cheapest valid combination
    if not valid_combinations:
        return ConvergedItinerary(
            is_successful=False,
            convergence_window_start=None,
            convergence_window_end=None,
            total_group_flight_cost=0,
            selected_flights=[],
            failure_reason=f"Could not find any combination of flights where all travelers arrive within {MAX_CONVERGENCE_GAP_HOURS} hours of each other."
        )
        
    # Sort by cost ascending
    valid_combinations.sort(key=lambda x: x["cost"])
    best = valid_combinations[0]
    
    return ConvergedItinerary(
        is_successful=True,
        convergence_window_start=best["earliest"].strftime("%Y-%m-%d %H:%M"),
        convergence_window_end=best["latest"].strftime("%Y-%m-%d %H:%M"),
        total_group_flight_cost=best["cost"],
        selected_flights=list(best["combo"]),
        failure_reason=None
    )
