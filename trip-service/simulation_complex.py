"""
MACI v2: Complex Multi-Agent Simulation (The Barcelona Birthday Trip)
=====================================================================
Simulates a real-world multi-turn group travel coordination scenario with:
- 6 travelers from 4 different origin cities
- Conflicting constraints (budgets, schedules, hotel preferences, dietary needs)
- Multi-turn negotiation (failed convergence -> user prompt -> re-plan)
- Full trace logging of every operation and API call
"""

import asyncio
import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from io import StringIO
from contextlib import redirect_stdout

from pydantic import BaseModel
from jinja2 import Template

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from app.tools.serp_client import SerpClient
from app.tools.flight_search import create_flight_search_tool
from app.tools.hotel_search import create_hotel_search_tool
from app.tools.local_search import create_local_search_tool, create_event_search_tool
from app.tools.price_intel import create_price_insights_tool, create_flight_deals_tool
from app.services.convergence import run_convergence_algorithm
from maci_core.schemas.ai import FlightProposal

# ── 0. Trace Infrastructure ───────────────────────────────────────────────

TRACE_FILE = Path(__file__).parent / "simulation_complex_trace.log"
SIMULATION_ID = str(uuid.uuid4())[:8]
_trace_entries: List[Dict[str, Any]] = []
_start_time = time.time()

def _elapsed() -> str:
    return f"{time.time() - _start_time:.3f}s"

def trace(category: str, agent: str, event: str, data: Any = None, **kwargs):
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "elapsed": _elapsed(),
        "simulation_id": SIMULATION_ID,
        "category": category,
        "agent": agent,
        "event": event,
        "data": data,
        **kwargs,
    }
    _trace_entries.append(entry)
    prefix = f"[{entry['elapsed']:>9s}] [{category:>14s}] [{agent:>20s}]"
    print(f"{prefix} {event}")
    if data and isinstance(data, dict):
        for k, v in data.items():
            val_str = str(v)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            print(f"{'':>50s} {k}: {val_str}")

def save_trace():
    json_path = TRACE_FILE.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(_trace_entries, f, indent=2, default=str)

    with open(TRACE_FILE, "w") as f:
        f.write("=" * 120 + "\n")
        f.write("MACI v2 — COMPLEX MULTI-AGENT SIMULATION TRACE\n")
        f.write(f"Simulation ID: {SIMULATION_ID}\n")
        f.write(f"Generated at: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total trace entries: {len(_trace_entries)}\n")
        f.write("=" * 120 + "\n\n")

        for i, entry in enumerate(_trace_entries):
            f.write(f"─── Entry #{i+1} ─────────────────────────────────────────────\n")
            f.write(f"  Timestamp : {entry['timestamp']}\n")
            f.write(f"  Elapsed   : {entry['elapsed']}\n")
            f.write(f"  Category  : {entry['category']}\n")
            f.write(f"  Agent     : {entry['agent']}\n")
            f.write(f"  Event     : {entry['event']}\n")
            if entry.get("data"):
                f.write(f"  Data      :\n")
                data_str = json.dumps(entry["data"], indent=4, default=str)
                for line in data_str.split("\n"):
                    f.write(f"    {line}\n")
            f.write("\n")

        f.write("\n" + "=" * 120 + "\n")
        f.write("EXECUTION SUMMARY\n")
        f.write("=" * 120 + "\n\n")

        categories = {}
        for e in _trace_entries:
            cat = e["category"]
            categories[cat] = categories.get(cat, 0) + 1
        f.write("Events by Category:\n")
        for cat, count in sorted(categories.items()):
            f.write(f"  {cat:>20s}: {count}\n")

        agents = {}
        for e in _trace_entries:
            ag = e["agent"]
            agents[ag] = agents.get(ag, 0) + 1
        f.write("\nEvents by Agent:\n")
        for ag, count in sorted(agents.items()):
            f.write(f"  {ag:>20s}: {count}\n")

    print(f"\n✅ Trace saved to:\n   Text: {TRACE_FILE}\n   JSON: {json_path}")

# ── 1. Environment Setup ─────────────────────────────────────────────────

def setup_environment():
    trace("SETUP", "simulation", "Setting up environment for real API access")
    os.environ["MACI_MOCK_MODE"] = "false"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://oai-maci-dev-de7cc.openai.azure.com/"
    
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url="https://kv-maci-dev-123.vault.azure.net", credential=credential)
        secret = client.get_secret("serpapi-key")
        os.environ["SERPAPI_API_KEY"] = secret.value
        trace("SETUP", "keyvault", "✅ SERPAPI_API_KEY loaded from Key Vault")
    except Exception as e:
        trace("SETUP", "keyvault", f"❌ Key Vault fetch failed: {e}")
        if not os.getenv("SERPAPI_API_KEY"):
            raise RuntimeError("Cannot proceed without SERPAPI_API_KEY")

def get_llm():
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment="o3",
        api_version="2024-12-01-preview",
        temperature=1,
        max_retries=10,
        azure_ad_token_provider=token_provider,
    )

class BaseProposals(BaseModel):
    proposals: List[FlightProposal]

async def run_flight_delegate(origin: str, destination: str, date: str, travelers: List[Dict[str, Any]]) -> List[FlightProposal]:
    agent_id = f"flight-delegate-{origin.lower()}-{str(uuid.uuid4())[:6]}"
    trace("AGENT_LIFECYCLE", agent_id, f"Agent CREATED for origin={origin}")
    
    with open(Path(__file__).parent / "app/prompts/flight_delegate.md") as f:
        template = Template(f.read())
    system_prompt = template.render(origin_airport=origin, destination=destination, outbound_date=date, travelers=travelers)
    
    llm = get_llm()
    serp_client = SerpClient(api_key=os.environ["SERPAPI_API_KEY"])
    flight_tool = create_flight_search_tool(serp_client)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Please search for flights from {origin} to {destination} on {date} and pick the top 3 options based on my constraints.")
    ]
    
    llm_with_tools = llm.bind_tools([flight_tool])
    trace("MESSAGE_CHAIN", agent_id, "Message #0: SystemMessage")
    trace("MESSAGE_CHAIN", agent_id, "Message #1: HumanMessage")
    
    for i in range(2):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        trace("MESSAGE_CHAIN", agent_id, f"Message #{len(messages)-1}: AIMessage")
        
        if not response.tool_calls:
            break
            
        for tool_call in response.tool_calls:
            if tool_call["name"] == "search_flights":
                tool_output = flight_tool.invoke(tool_call["args"])
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
                trace("MESSAGE_CHAIN", agent_id, f"Message #{len(messages)-1}: ToolMessage")
    
    final_output = messages[-1].content
    trace("AGENT_OUTPUT", agent_id, "Raw agent output", data={"final_message": final_output})
    
    structured_llm = llm.with_structured_output(BaseProposals)
    extraction_prompt = f"Extract the flight proposals from the following text into the structured format:\n\n{final_output}"
    trace("SCHEMA_EXTRACTION", agent_id, "Extracting structured FlightProposals")
    
    try:
        parsed_result = structured_llm.invoke(extraction_prompt)
        proposals = parsed_result.proposals if parsed_result else []
    except Exception as e:
        trace("SCHEMA_EXTRACTION", agent_id, f"❌ Extraction failed: {e}")
        proposals = []
        
    for p in proposals:
        p.origin_airport = origin
    
    trace("AGENT_LIFECYCLE", agent_id, f"Agent COMPLETED with {len(proposals)} proposals")
    return proposals

async def run_negotiation_agent(failure_reason: str, constraints: dict) -> str:
    agent_id = f"negotiation-agent-{str(uuid.uuid4())[:6]}"
    trace("AGENT_LIFECYCLE", agent_id, "Negotiation Agent CREATED")
    
    with open(Path(__file__).parent / "app/prompts/negotiation_agent.md") as f:
        template = Template(f.read())
    system_prompt = template.render(
        destination="Barcelona, Spain", 
        dates=constraints["outbound_date"], 
        total_travelers=6,
        failure_reason=failure_reason,
        constraints_summary=json.dumps(constraints["travelers"], indent=2)
    )
    
    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="The convergence failed. Please propose a compromise to the group.")
    ]
    
    response = llm.invoke(messages)
    trace("AGENT_OUTPUT", agent_id, "Negotiation Output", data={"proposal": response.content})
    return response.content

async def run_hotel_agent(destination: str, dates: str, group_profile: dict) -> str:
    agent_id = f"hotel-agent-{str(uuid.uuid4())[:6]}"
    trace("AGENT_LIFECYCLE", agent_id, "Hotel Agent CREATED")
    
    with open(Path(__file__).parent / "app/prompts/hotel_agent.md") as f:
        template = Template(f.read())
    system_prompt = template.render(
        destination=destination,
        dates=dates,
        total_travelers=group_profile["total_travelers"],
        rooms_needed=group_profile["rooms_needed"],
        total_budget_usd=group_profile["total_budget_usd"],
        budget_per_night_usd=group_profile["budget_per_night_usd"],
        special_requests=group_profile["special_requests"]
    )
    
    llm = get_llm()
    serp_client = SerpClient(api_key=os.environ["SERPAPI_API_KEY"])
    hotel_tool = create_hotel_search_tool(serp_client)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please search for hotels based on our profile.")
    ]
    
    llm_with_tools = llm.bind_tools([hotel_tool])
    for i in range(2):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tool_call in response.tool_calls:
            if tool_call["name"] == "search_hotels":
                tool_output = hotel_tool.invoke(tool_call["args"])
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
                
    trace("AGENT_OUTPUT", agent_id, "Hotel Agent Output", data={"final_message": messages[-1].content})
    return messages[-1].content

async def run_activity_agent(destination: str, dates: str, group_profile: dict) -> str:
    agent_id = f"activity-agent-{str(uuid.uuid4())[:6]}"
    trace("AGENT_LIFECYCLE", agent_id, "Activity Agent CREATED")
    
    with open(Path(__file__).parent / "app/prompts/activity_agent.md") as f:
        template = Template(f.read())
    system_prompt = template.render(
        destination=destination,
        dates=dates,
        total_travelers=group_profile["total_travelers"],
        dietary_restrictions=group_profile["dietary_restrictions"],
        accessibility_needs=group_profile["accessibility_needs"],
        group_interests=group_profile["group_interests"]
    )
    
    llm = get_llm()
    serp_client = SerpClient(api_key=os.environ["SERPAPI_API_KEY"])
    places_tool = create_local_search_tool(serp_client)
    events_tool = create_event_search_tool(serp_client)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please build our activity itinerary.")
    ]
    
    llm_with_tools = llm.bind_tools([places_tool, events_tool])
    for i in range(3):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tool_call in response.tool_calls:
            tool_fn = places_tool if tool_call["name"] == "search_places" else events_tool
            tool_output = tool_fn.invoke(tool_call["args"])
            messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
            
    trace("AGENT_OUTPUT", agent_id, "Activity Agent Output", data={"final_message": messages[-1].content})
    return messages[-1].content

async def run_price_intel_agent(destination: str, dates: str, origins: List[str]) -> str:
    agent_id = f"price-intel-agent-{str(uuid.uuid4())[:6]}"
    trace("AGENT_LIFECYCLE", agent_id, "Price Intel Agent CREATED")
    
    with open(Path(__file__).parent / "app/prompts/price_intel_agent.md") as f:
        template = Template(f.read())
    system_prompt = template.render(
        destination=destination,
        dates=dates,
        origins=", ".join(origins)
    )
    
    llm = get_llm()
    serp_client = SerpClient(api_key=os.environ["SERPAPI_API_KEY"])
    insights_tool = create_price_insights_tool(serp_client)
    deals_tool = create_flight_deals_tool(serp_client)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Provide your pricing recommendation.")
    ]
    
    llm_with_tools = llm.bind_tools([insights_tool, deals_tool])
    for i in range(3):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tool_call in response.tool_calls:
            tool_fn = insights_tool if tool_call["name"] == "get_price_insights" else deals_tool
            tool_output = tool_fn.invoke(tool_call["args"])
            messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
            
    trace("AGENT_OUTPUT", agent_id, "Price Intel Agent Output", data={"final_message": messages[-1].content})
    return messages[-1].content


# ── MAIN SIMULATION ──────────────────────────────────────────────────────

async def main():
    setup_environment()
    
    test_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    scenario = {
        "destination": "Barcelona, Spain",
        "outbound_date": test_date,
        "travelers": [
            {"traveler_id": "T1_Priya", "origin_airport": "BOM", "budget_flights_usd": 600, "earliest_departure": f"{test_date} 00:00"},
            {"traveler_id": "T2_Marcus", "origin_airport": "ORD", "budget_flights_usd": 450, "earliest_departure": f"{test_date} 10:00"},
            {"traveler_id": "T3_Yuki", "origin_airport": "SFO", "budget_flights_usd": 900, "earliest_departure": f"{test_date} 00:00"},
            {"traveler_id": "T4_Carlos", "origin_airport": "SFO", "budget_flights_usd": 500, "earliest_departure": f"{test_date} 00:00"},
            {"traveler_id": "T5_Aisha", "origin_airport": "JFK", "budget_flights_usd": 350, "earliest_departure": f"{test_date} 00:00"},
            {"traveler_id": "T6_Emma", "origin_airport": "JFK", "budget_flights_usd": 200, "earliest_departure": f"{test_date} 00:00"},
        ]
    }
    origins = ["BOM", "ORD", "SFO", "JFK"]
    
    trace("SCENARIO", "simulation", "Turn 1: Initial Search")
    
    all_proposals = {}
    for origin in origins:
        travelers_in_cluster = [t for t in scenario["travelers"] if t["origin_airport"] == origin]
        proposals = await run_flight_delegate(origin, scenario["destination"], scenario["outbound_date"], travelers_in_cluster)
        all_proposals[origin] = proposals
        
    proposals_by_origin = [{"origin": o, "proposals": all_proposals[o]} for o in origins]
    convergence_result = run_convergence_algorithm(proposals_by_origin)
    trace("CONVERGENCE", "orchestrator", "Convergence Result Turn 1", data={"success": convergence_result.is_successful, "reason": convergence_result.failure_reason})
    
    if not convergence_result.is_successful:
        trace("SCENARIO", "simulation", "Turn 2: Negotiation (Budget Adjustment)")
        negotiation_proposal = await run_negotiation_agent(convergence_result.failure_reason, scenario)
        
        # Simulate User Response: Priya increases budget to $850
        trace("SCENARIO", "user", "User accepts budget increase for BOM")
        for t in scenario["travelers"]:
            if t["traveler_id"] == "T1_Priya":
                t["budget_flights_usd"] = 850
                
        # Re-run BOM
        travelers_in_cluster = [t for t in scenario["travelers"] if t["origin_airport"] == "BOM"]
        proposals = await run_flight_delegate("BOM", scenario["destination"], scenario["outbound_date"], travelers_in_cluster)
        all_proposals["BOM"] = proposals
        
        proposals_by_origin = [{"origin": o, "proposals": all_proposals[o]} for o in origins]
        convergence_result = run_convergence_algorithm(proposals_by_origin)
        trace("CONVERGENCE", "orchestrator", "Convergence Result Turn 2", data={"success": convergence_result.is_successful, "reason": convergence_result.failure_reason})
        
        if not convergence_result.is_successful:
            trace("SCENARIO", "simulation", "Turn 3: Negotiation (Timing Adjustment)")
            negotiation_proposal = await run_negotiation_agent(convergence_result.failure_reason, scenario)
            
            # Simulate User Response: Marcus agrees to fly at 8am
            trace("SCENARIO", "user", "User accepts earlier departure for ORD")
            for t in scenario["travelers"]:
                if t["traveler_id"] == "T2_Marcus":
                    t["earliest_departure"] = f"{test_date} 08:00"
                    
            # Re-run ORD
            travelers_in_cluster = [t for t in scenario["travelers"] if t["origin_airport"] == "ORD"]
            proposals = await run_flight_delegate("ORD", scenario["destination"], scenario["outbound_date"], travelers_in_cluster)
            all_proposals["ORD"] = proposals
            
            proposals_by_origin = [{"origin": o, "proposals": all_proposals[o]} for o in origins]
            convergence_result = run_convergence_algorithm(proposals_by_origin)
            trace("CONVERGENCE", "orchestrator", "Convergence Result Turn 3", data={"success": convergence_result.is_successful, "reason": convergence_result.failure_reason})
    
    trace("SCENARIO", "simulation", "Turn 4: Hotel Search")
    hotel_profile = {
        "total_travelers": 6,
        "rooms_needed": 3,
        "total_budget_usd": 470, # (80+60+120+50+70+90)
        "budget_per_night_usd": 78,
        "special_requests": "Split into boutique luxury (for Yuki/Emma) and budget/free-breakfast (for Aisha/Marcus). Also need wheelchair accessibility."
    }
    hotel_result = await run_hotel_agent(scenario["destination"], scenario["outbound_date"] + " to " + (datetime.now() + timedelta(days=64)).strftime("%Y-%m-%d"), hotel_profile)
    
    trace("SCENARIO", "simulation", "Turn 5: Activity Search")
    activity_profile = {
        "total_travelers": 6,
        "dietary_restrictions": "Vegetarian",
        "accessibility_needs": "Wheelchair accessible",
        "group_interests": "Art, Food tours, Culture"
    }
    activity_result = await run_activity_agent(scenario["destination"], scenario["outbound_date"], activity_profile)
    
    trace("SCENARIO", "simulation", "Turn 6: Price Intelligence")
    price_result = await run_price_intel_agent(scenario["destination"], scenario["outbound_date"], origins)
    
    trace("REPORT", "simulation", "Simulation Complete!")
    save_trace()

if __name__ == "__main__":
    asyncio.run(main())
