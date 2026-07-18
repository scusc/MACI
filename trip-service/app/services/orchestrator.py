"""
LangGraph Multi-Agent Orchestrator

This module defines the StateGraph for MACI v2.
The workflow is:
1. Intake (User defines trip & constraints)
2. Fan-out (Map): Spawn parallel Flight Delegates for each origin
3. Convergence: Calculate time windows and select the best flight for each origin
4. Fan-out (Map): Spawn Hotel and Activity Agents based on converged destination/dates
5. Itinerary Builder (Reduce): Assemble final JSON
"""

import operator
from typing import Annotated, Any, Dict, List, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from maci_core.schemas.ai import FlightProposal, HotelProposal, ActivityItem, GroupItinerary, ConvergedItinerary

# ── 1. State Definitions ──────────────────────────────────────────────────────

class TravelerConstraint(TypedDict):
    traveler_id: str
    origin_airport: str
    earliest_departure: str
    latest_arrival: str
    budget_flights_usd: int

class TripState(TypedDict):
    """The global state for the entire trip orchestration."""
    destination: str
    outbound_date: str
    return_date: str | None
    travelers: List[TravelerConstraint]
    
    # Map-Reduce aggregation fields
    flight_proposals: Annotated[List[Dict[str, Any]], operator.add]
    
    # Post-convergence state
    converged_itinerary: ConvergedItinerary | None
    
    # Final outputs
    hotels: List[HotelProposal]
    activities: List[ActivityItem]
    price_intelligence: str

class FlightDelegateState(TypedDict):
    """The local state for a single Flight Delegate (one per origin)."""
    origin_airport: str
    destination: str
    outbound_date: str
    travelers: List[TravelerConstraint]


# ── 2. Nodes ─────────────────────────────────────────────────────────────────

async def intake_node(state: TripState) -> TripState:
    """Validates input and prepares for fan-out."""
    return state


def spawn_flight_delegates(state: TripState) -> List[Send]:
    """
    Map step: Group travelers by origin airport and spawn a FlightDelegate
    for each unique origin.
    """
    origins = {}
    for t in state["travelers"]:
        orig = t["origin_airport"]
        if orig not in origins:
            origins[orig] = []
        origins[orig].append(t)
        
    sends = []
    for origin, travelers in origins.items():
        local_state = FlightDelegateState(
            origin_airport=origin,
            destination=state["destination"],
            outbound_date=state["outbound_date"],
            travelers=travelers
        )
        sends.append(Send("flight_delegate", local_state))
        
    return sends


async def flight_delegate_node(state: FlightDelegateState) -> Dict[str, Any]:
    """
    Local node that executes the LangChain agent for a single origin.
    (This will call the Azure OpenAI LLM with the search_flights tool)
    """
    from app.services.ai_delegate import run_flight_delegate
    
    # Run the LLM agent to get proposals for this origin
    proposals = await run_flight_delegate(
        origin=state["origin_airport"],
        destination=state["destination"],
        date=state["outbound_date"],
        travelers=state["travelers"]
    )
    
    # The output is reduced into the global state's `flight_proposals` list
    return {"flight_proposals": [{"origin": state["origin_airport"], "proposals": proposals}]}


async def convergence_node(state: TripState) -> Dict[str, Any]:
    """
    Deterministic Python logic (no LLM) that calculates the optimal
    combination of flights so everyone arrives together.
    """
    from app.services.convergence import run_convergence_algorithm
    
    proposals_by_origin = state["flight_proposals"]
    converged = run_convergence_algorithm(proposals_by_origin)
    
    return {"converged_itinerary": converged}


async def hotel_agent_node(state: TripState) -> Dict[str, Any]:
    """Runs the LLM agent to find group hotels."""
    # Placeholder for Phase 6 LLM integration
    return {"hotels": []}


async def activity_agent_node(state: TripState) -> Dict[str, Any]:
    """Runs the LLM agent to find group activities."""
    # Placeholder for Phase 6 LLM integration
    return {"activities": []}


async def price_intel_node(state: TripState) -> Dict[str, Any]:
    """Runs the Price Intel agent."""
    # Placeholder for Phase 7
    return {"price_intelligence": "Book now, prices are low!"}


async def itinerary_builder_node(state: TripState) -> Dict[str, Any]:
    """Finalizes the structured JSON output."""
    return state


# ── 3. Graph Definition ──────────────────────────────────────────────────────

def build_orchestrator_graph() -> StateGraph:
    """Builds and compiles the MACI LangGraph workflow."""
    builder = StateGraph(TripState)

    # Add Nodes
    builder.add_node("intake", intake_node)
    builder.add_node("flight_delegate", flight_delegate_node)
    builder.add_node("convergence", convergence_node)
    builder.add_node("hotel_agent", hotel_agent_node)
    builder.add_node("activity_agent", activity_agent_node)
    builder.add_node("price_intel", price_intel_node)
    builder.add_node("itinerary_builder", itinerary_builder_node)

    # Edges
    builder.add_edge(START, "intake")
    
    # Fan-out to flights using conditional edges based on the Send API
    builder.add_conditional_edges("intake", spawn_flight_delegates)
    
    # Fan-in from flights to convergence
    builder.add_edge("flight_delegate", "convergence")
    
    # After convergence, fan-out to destination agents
    builder.add_edge("convergence", "hotel_agent")
    builder.add_edge("convergence", "activity_agent")
    builder.add_edge("convergence", "price_intel")
    
    # Fan-in to final builder
    builder.add_edge("hotel_agent", "itinerary_builder")
    builder.add_edge("activity_agent", "itinerary_builder")
    builder.add_edge("price_intel", "itinerary_builder")
    
    builder.add_edge("itinerary_builder", END)

    return builder.compile()
