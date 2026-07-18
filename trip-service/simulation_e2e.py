"""
MACI v2: Comprehensive End-to-End Simulation & Trace
=====================================================
This script simulates a REAL WORLD multi-turn group travel coordination
scenario and captures an exhaustive trace of every operation:

  - Every agent instantiation with names, IDs, and timestamps
  - Every LLM call with full input/output context
  - Every SerpAPI call with request params and parsed responses
  - Every context handoff between agents
  - Every orchestrator decision with justifications
  - The convergence algorithm inputs, computation, and output
  - Full timing metrics and sequence of execution

The trace is saved to a local text file for analysis.

IMPORTANT: This is a SIMULATION-ONLY script. It is NOT production code.
After running, revert any temporary changes to production files.
"""

import asyncio
import os
import sys
import json
import time
import uuid
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from io import StringIO
from contextlib import redirect_stdout

# ── 0. Trace Infrastructure ───────────────────────────────────────────────

TRACE_FILE = Path(__file__).parent / "simulation_trace.log"
SIMULATION_ID = str(uuid.uuid4())[:8]
_trace_entries: List[Dict[str, Any]] = []
_start_time = time.time()


def _elapsed() -> str:
    return f"{time.time() - _start_time:.3f}s"


def trace(category: str, agent: str, event: str, data: Any = None, **kwargs):
    """Record a single trace entry with timestamp, agent, event, and payload."""
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
    # Also print live for monitoring
    prefix = f"[{entry['elapsed']:>9s}] [{category:>14s}] [{agent:>20s}]"
    print(f"{prefix} {event}")
    if data and isinstance(data, dict):
        for k, v in data.items():
            val_str = str(v)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            print(f"{'':>50s} {k}: {val_str}")


def save_trace():
    """Write the full trace to disk as both structured JSON and readable text."""
    # JSON trace (machine readable)
    json_path = TRACE_FILE.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(_trace_entries, f, indent=2, default=str)

    # Human-readable text trace
    with open(TRACE_FILE, "w") as f:
        f.write("=" * 120 + "\n")
        f.write("MACI v2 — COMPREHENSIVE END-TO-END SIMULATION TRACE\n")
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

        # Summary section
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
    """Configure environment for real API access."""
    trace("SETUP", "simulation", "Setting up environment for real API access")

    # Disable mock mode
    os.environ["MACI_MOCK_MODE"] = "false"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://oai-maci-dev-de7cc.openai.azure.com/"
    trace("SETUP", "simulation", "Environment variables set", data={
        "MACI_MOCK_MODE": "false",
        "AZURE_OPENAI_ENDPOINT": os.environ["AZURE_OPENAI_ENDPOINT"],
    })

    # Fetch SerpAPI key from Azure Key Vault
    trace("SETUP", "keyvault", "Fetching SERPAPI_API_KEY from Azure Key Vault")
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(
            vault_url="https://kv-maci-dev-123.vault.azure.net",
            credential=credential,
        )
        secret = client.get_secret("serpapi-key")
        os.environ["SERPAPI_API_KEY"] = secret.value
        trace("SETUP", "keyvault", "✅ SERPAPI_API_KEY loaded from Key Vault", data={
            "key_vault": "kv-maci-dev-123",
            "secret_name": "serpapi-key",
            "key_length": len(secret.value),
            "auth_method": "DefaultAzureCredential (AzureCliCredential)"
        })
    except Exception as e:
        trace("SETUP", "keyvault", f"❌ Key Vault fetch failed: {e}")
        if not os.getenv("SERPAPI_API_KEY"):
            raise RuntimeError("Cannot proceed without SERPAPI_API_KEY")


# ── 2. Scenario Definition ───────────────────────────────────────────────

def build_scenario() -> Dict[str, Any]:
    """
    Simulate a real-world group trip planning conversation.
    
    SCENARIO: A group of 4 friends from 3 different cities want to meet up
    in Barcelona for a long weekend. They have different budgets and 
    schedule constraints.
    """
    test_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

    scenario = {
        "conversation_id": f"conv-{SIMULATION_ID}",
        "user_query": (
            "Hey MACI! We're a group of 3 friends wanting to meet up in Barcelona "
            "for a trip. Here are our details:\n"
            "- Alice (from SFO): Budget $1200, flexible all day\n"
            "- Bob (from SFO): Budget $1000, can't leave before 8am\n"
            "- Carol (from JFK): Budget $800, flexible all day\n"
            f"We want to fly out on {test_date}. Find us the best flights "
            "so we all arrive around the same time!"
        ),
        "destination": "Barcelona, Spain",
        "outbound_date": test_date,
        "return_date": None,
        "travelers": [
            {
                "traveler_id": "T1_Alice",
                "origin_airport": "SFO",
                "earliest_departure": f"{test_date} 06:00",
                "budget_flights_usd": 1200,
            },
            {
                "traveler_id": "T2_Bob",
                "origin_airport": "SFO",
                "earliest_departure": f"{test_date} 08:00",
                "budget_flights_usd": 1000,
            },
            {
                "traveler_id": "T3_Carol",
                "origin_airport": "JFK",
                "earliest_departure": f"{test_date} 06:00",
                "budget_flights_usd": 800,
            },
        ],
    }

    trace("SCENARIO", "simulation", "User query received", data={
        "conversation_id": scenario["conversation_id"],
        "user_query": scenario["user_query"],
    })
    trace("SCENARIO", "simulation", "Parsed traveler constraints", data={
        "destination": scenario["destination"],
        "outbound_date": scenario["outbound_date"],
        "num_travelers": len(scenario["travelers"]),
        "unique_origins": list(set(t["origin_airport"] for t in scenario["travelers"])),
        "travelers": scenario["travelers"],
    })

    return scenario


# ── 3. Instrumented AI Delegate ──────────────────────────────────────────
# We monkey-patch the production code to inject tracing at every level.

async def traced_run_flight_delegate(
    origin: str,
    destination: str,
    date: str,
    travelers: List[Dict[str, Any]],
) -> List[Any]:
    """
    Runs the flight delegate with comprehensive tracing injected at every step.
    """
    agent_id = f"flight-delegate-{origin.lower()}-{str(uuid.uuid4())[:6]}"
    delegate_start = time.time()

    trace("AGENT_LIFECYCLE", agent_id, f"Agent CREATED for origin={origin}", data={
        "agent_type": "FlightDelegate (ReAct Agent)",
        "model": "o3 (Azure OpenAI)",
        "deployment": "o3",
        "api_version": "2024-12-01-preview",
        "origin": origin,
        "destination": destination,
        "date": date,
        "num_travelers": len(travelers),
        "traveler_ids": [t["traveler_id"] for t in travelers],
    })

    # ── Step 1: Build the LLM client
    trace("LLM_CONFIG", agent_id, "Constructing AzureChatOpenAI client", data={
        "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
        "azure_deployment": "o3",
        "api_version": "2024-12-01-preview",
        "temperature": 1,
        "max_retries": 10,
        "max_tokens": 4000,
        "auth_method": "Entra ID (azure_ad_token_provider via DefaultAzureCredential)",
    })

    from app.services.ai_delegate import get_azure_openai_client, MOCK_MODE
    from app.tools.serp_client import SerpClient
    from app.tools.flight_search import create_flight_search_tool
    from maci_core.schemas.ai import DelegateResponse

    llm = get_azure_openai_client()
    trace("LLM_CONFIG", agent_id, "✅ AzureChatOpenAI client initialized")

    # ── Step 2: Build the SerpAPI tool
    serp_client = SerpClient(mock_mode=MOCK_MODE)
    original_search = serp_client.search

    serp_call_log = []

    def traced_search(engine: str, params: dict) -> dict:
        """Wrapper that traces every SerpAPI call."""
        call_start = time.time()
        call_id = f"serp-{len(serp_call_log)+1}"

        trace("API_CALL", agent_id, f"SerpAPI REQUEST → {engine}", data={
            "call_id": call_id,
            "engine": engine,
            "params": {k: v for k, v in params.items() if k != "api_key"},
            "budget_remaining": serp_client.calls_remaining,
        })

        result = original_search(engine, params)
        call_duration = time.time() - call_start

        # Parse the response for trace
        best_flights = result.get("best_flights", [])
        other_flights = result.get("other_flights", [])
        price_insights = result.get("price_insights", {})

        response_summary = {
            "call_id": call_id,
            "duration_ms": round(call_duration * 1000),
            "best_flights_count": len(best_flights),
            "other_flights_count": len(other_flights),
            "total_options": len(best_flights) + len(other_flights),
            "price_insights": {
                "lowest_price": price_insights.get("lowest_price"),
                "price_level": price_insights.get("price_level"),
                "typical_range": price_insights.get("typical_price_range"),
            },
            "budget_remaining_after": serp_client.calls_remaining,
        }

        # Extract individual flight details
        all_flights = best_flights + other_flights
        flight_summaries = []
        for f in all_flights[:5]:
            segs = f.get("flights", [])
            first = segs[0] if segs else {}
            last = segs[-1] if segs else {}
            flight_summaries.append({
                "price": f.get("price"),
                "duration_min": f.get("total_duration"),
                "airline": first.get("airline"),
                "flight_number": first.get("flight_number"),
                "departure": first.get("departure_airport", {}).get("time"),
                "arrival": last.get("arrival_airport", {}).get("time"),
                "stops": len(segs) - 1,
            })
        response_summary["flights"] = flight_summaries

        trace("API_RESPONSE", agent_id, f"SerpAPI RESPONSE ← {engine}", data=response_summary)
        serp_call_log.append(response_summary)
        return result

    serp_client.search = traced_search
    flight_tool = create_flight_search_tool(serp_client)
    trace("TOOL_SETUP", agent_id, "Flight search tool created and bound to agent", data={
        "tool_name": "search_flights",
        "tool_type": "LangChain @tool with Pydantic schema",
        "mock_mode": MOCK_MODE,
    })

    # ── Step 3: Build the system prompt
    from langchain_core.prompts import PromptTemplate
    prompt_path = Path(__file__).parent / "app" / "prompts" / "flight_delegate.md"
    prompt_template = PromptTemplate.from_file(str(prompt_path), template_format="jinja2")
    system_prompt = prompt_template.invoke({
        "origin_airport": origin,
        "destination": destination,
        "outbound_date": date,
        "travelers": travelers,
    }).to_string()

    trace("PROMPT", agent_id, "System prompt rendered from template", data={
        "template_file": "flight_delegate.md",
        "rendered_prompt": system_prompt,
        "prompt_length_chars": len(system_prompt),
    })

    user_message = f"Please search for flights from {origin} to {destination} on {date} and pick the top 3 options based on my constraints."
    trace("PROMPT", agent_id, "User message constructed", data={
        "user_message": user_message,
    })

    # ── Step 4: Execute the ReAct Agent loop
    from langgraph.prebuilt import create_react_agent
    agent_executor = create_react_agent(llm, tools=[flight_tool])

    inputs = {
        "messages": [
            ("system", system_prompt),
            ("user", user_message),
        ]
    }

    trace("AGENT_EXECUTION", agent_id, "ReAct agent loop STARTED", data={
        "input_messages_count": 2,
        "tools_available": ["search_flights"],
    })

    react_start = time.time()
    result = await agent_executor.ainvoke(inputs)
    react_duration = time.time() - react_start

    # Trace all messages from the ReAct loop
    messages = result.get("messages", [])
    trace("AGENT_EXECUTION", agent_id, f"ReAct agent loop COMPLETED in {react_duration:.1f}s", data={
        "duration_s": round(react_duration, 2),
        "total_messages_in_chain": len(messages),
        "serp_api_calls_made": len(serp_call_log),
    })

    # Log each message in the chain
    for idx, msg in enumerate(messages):
        msg_type = type(msg).__name__
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", None)

        msg_data = {
            "index": idx,
            "type": msg_type,
            "content_length": len(str(content)),
            "content_preview": str(content)[:500] if content else "(empty)",
        }
        if tool_calls:
            msg_data["tool_calls"] = [
                {"name": tc.get("name"), "args": tc.get("args")} for tc in tool_calls
            ]

        trace("MESSAGE_CHAIN", agent_id, f"Message #{idx}: {msg_type}", data=msg_data)

    final_message = messages[-1].content if messages else ""
    trace("AGENT_OUTPUT", agent_id, "Raw agent output (pre-schema extraction)", data={
        "final_message_length": len(final_message),
        "final_message": final_message[:2000],
    })

    # ── Step 5: Structured output extraction
    trace("SCHEMA_EXTRACTION", agent_id, "Extracting structured FlightProposals via with_structured_output")

    extract_start = time.time()
    extractor = llm.with_structured_output(DelegateResponse)
    structured = await extractor.ainvoke([
        ("system", "Extract the flight proposals from the following text into the structured schema. Origin is " + origin),
        ("user", final_message),
    ])
    extract_duration = time.time() - extract_start

    proposals = structured.proposals
    trace("SCHEMA_EXTRACTION", agent_id, f"✅ Extracted {len(proposals)} proposals in {extract_duration:.1f}s", data={
        "duration_s": round(extract_duration, 2),
        "num_proposals": len(proposals),
        "proposals": [
            {
                "origin": p.origin_airport,
                "price_usd": p.total_price_usd,
                "duration_min": p.total_duration_min,
                "segments": len(p.segments),
                "reasoning": p.reasoning[:200] if p.reasoning else None,
                "segment_details": [
                    {
                        "from": s.departure_airport,
                        "to": s.arrival_airport,
                        "depart": s.departure_time,
                        "arrive": s.arrival_time,
                        "airline": s.airline,
                        "flight": s.flight_number,
                        "duration_min": s.duration_min,
                    }
                    for s in p.segments
                ],
            }
            for p in proposals
        ],
    })

    total_duration = time.time() - delegate_start
    trace("AGENT_LIFECYCLE", agent_id, f"Agent COMPLETED in {total_duration:.1f}s", data={
        "total_duration_s": round(total_duration, 2),
        "llm_calls": len(messages) - 1,  # subtract the input messages
        "serp_api_calls": len(serp_call_log),
        "proposals_returned": len(proposals),
    })

    return proposals


# ── 4. Instrumented Orchestrator ──────────────────────────────────────────

async def run_orchestrator(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs the LangGraph orchestrator with full tracing.
    We execute it manually step-by-step instead of using the compiled graph
    so we can trace the map-reduce fan-out/fan-in and convergence.
    """
    trace("ORCHESTRATOR", "orchestrator", "═══ ORCHESTRATOR STARTED ═══", data={
        "destination": scenario["destination"],
        "outbound_date": scenario["outbound_date"],
        "num_travelers": len(scenario["travelers"]),
    })

    # ── Step 1: Intake
    trace("ORCHESTRATOR", "intake_node", "Intake node — validating input")
    origins = {}
    for t in scenario["travelers"]:
        orig = t["origin_airport"]
        if orig not in origins:
            origins[orig] = []
        origins[orig].append(t)

    trace("ORCHESTRATOR", "intake_node", "Travelers grouped by origin", data={
        "origin_groups": {
            orig: {
                "num_travelers": len(travelers),
                "traveler_ids": [t["traveler_id"] for t in travelers],
                "min_budget": min(t["budget_flights_usd"] for t in travelers),
                "max_budget": max(t["budget_flights_usd"] for t in travelers),
            }
            for orig, travelers in origins.items()
        },
    })

    # ── Step 2: Fan-out (Map) — Flight Delegates
    trace("ORCHESTRATOR", "orchestrator", "═══ MAP PHASE: Spawning Flight Delegates ═══", data={
        "num_delegates": len(origins),
        "origins": list(origins.keys()),
        "execution_mode": "SEQUENTIAL (to avoid Azure OpenAI 429 rate limits on o3)",
    })

    all_proposals = []
    for origin, travelers in origins.items():
        trace("ORCHESTRATOR", "orchestrator", f"Dispatching FlightDelegate for {origin}", data={
            "origin": origin,
            "destination": scenario["destination"],
            "date": scenario["outbound_date"],
            "travelers_in_cluster": [t["traveler_id"] for t in travelers],
        })

        proposals = await traced_run_flight_delegate(
            origin=origin,
            destination=scenario["destination"],
            date=scenario["outbound_date"],
            travelers=travelers,
        )

        all_proposals.append({"origin": origin, "proposals": proposals})

        trace("ORCHESTRATOR", "orchestrator", f"FlightDelegate for {origin} returned {len(proposals)} proposals", data={
            "origin": origin,
            "num_proposals": len(proposals),
        })

    # ── Step 3: Fan-in (Reduce) — Convergence
    trace("ORCHESTRATOR", "convergence_node", "═══ REDUCE PHASE: Running Convergence Algorithm ═══")

    trace("CONVERGENCE", "convergence_node", "Convergence inputs", data={
        "num_origins": len(all_proposals),
        "proposals_per_origin": {
            item["origin"]: len(item["proposals"]) for item in all_proposals
        },
        "all_proposals_summary": [
            {
                "origin": item["origin"],
                "proposals": [
                    {
                        "price": p.total_price_usd if hasattr(p, "total_price_usd") else p.get("total_price_usd"),
                        "duration": p.total_duration_min if hasattr(p, "total_duration_min") else p.get("total_duration_min"),
                        "segments": len(p.segments if hasattr(p, "segments") else p.get("segments", [])),
                        "last_arrival": (
                            (p.segments[-1].arrival_time if hasattr(p.segments[-1], "arrival_time") else p.segments[-1].get("arrival_time"))
                            if (p.segments if hasattr(p, "segments") else p.get("segments", []))
                            else "N/A"
                        ),
                    }
                    for p in item["proposals"]
                ],
            }
            for item in all_proposals
        ],
    })

    from app.services.convergence import run_convergence_algorithm
    converge_start = time.time()
    converged = run_convergence_algorithm(all_proposals)
    converge_duration = time.time() - converge_start

    is_success = converged.is_successful if hasattr(converged, "is_successful") else converged.get("is_successful")

    trace("CONVERGENCE", "convergence_node", f"Convergence RESULT: {'✅ SUCCESS' if is_success else '❌ FAILED'}", data={
        "duration_ms": round(converge_duration * 1000),
        "is_successful": is_success,
        "convergence_window_start": converged.convergence_window_start if hasattr(converged, "convergence_window_start") else converged.get("convergence_window_start"),
        "convergence_window_end": converged.convergence_window_end if hasattr(converged, "convergence_window_end") else converged.get("convergence_window_end"),
        "total_group_flight_cost": converged.total_group_flight_cost if hasattr(converged, "total_group_flight_cost") else converged.get("total_group_flight_cost"),
        "failure_reason": converged.failure_reason if hasattr(converged, "failure_reason") else converged.get("failure_reason"),
        "selected_flights_count": len(converged.selected_flights if hasattr(converged, "selected_flights") else converged.get("selected_flights", [])),
    })

    if is_success:
        flights = converged.selected_flights if hasattr(converged, "selected_flights") else converged.get("selected_flights", [])
        for f in flights:
            if hasattr(f, "origin_airport"):
                trace("CONVERGENCE", "convergence_node", f"Selected flight from {f.origin_airport}: ${f.total_price_usd}", data={
                    "origin": f.origin_airport,
                    "price_usd": f.total_price_usd,
                    "duration_min": f.total_duration_min,
                    "segments": [
                        {
                            "from": s.departure_airport,
                            "to": s.arrival_airport,
                            "depart": s.departure_time,
                            "arrive": s.arrival_time,
                            "airline": s.airline,
                        }
                        for s in f.segments
                    ],
                    "reasoning": f.reasoning,
                })

    # ── Step 4: Post-convergence nodes (placeholders)
    trace("ORCHESTRATOR", "hotel_agent", "Hotel Agent node (placeholder — Phase 6)")
    trace("ORCHESTRATOR", "activity_agent", "Activity Agent node (placeholder — Phase 6)")
    trace("ORCHESTRATOR", "price_intel", "Price Intel node (placeholder — Phase 7)")
    trace("ORCHESTRATOR", "itinerary_builder", "Itinerary Builder — assembling final output")

    final_state = {
        "destination": scenario["destination"],
        "outbound_date": scenario["outbound_date"],
        "return_date": scenario["return_date"],
        "travelers": scenario["travelers"],
        "flight_proposals": all_proposals,
        "converged_itinerary": converged,
        "hotels": [],
        "activities": [],
        "price_intelligence": "N/A — Phase 7",
    }

    trace("ORCHESTRATOR", "orchestrator", "═══ ORCHESTRATOR COMPLETED ═══", data={
        "convergence_success": is_success,
    })

    return final_state


# ── 5. Final Report Generator ────────────────────────────────────────────

def generate_report(scenario: Dict, final_state: Dict):
    """Generate a human-readable summary report appended to the trace file."""
    trace("REPORT", "simulation", "═══ GENERATING FINAL REPORT ═══")

    converged = final_state["converged_itinerary"]
    is_success = converged.is_successful if hasattr(converged, "is_successful") else converged.get("is_successful")

    report = {
        "simulation_id": SIMULATION_ID,
        "scenario": {
            "destination": scenario["destination"],
            "date": scenario["outbound_date"],
            "travelers": len(scenario["travelers"]),
            "origins": list(set(t["origin_airport"] for t in scenario["travelers"])),
        },
        "execution_metrics": {
            "total_time_s": _elapsed(),
            "total_trace_entries": len(_trace_entries),
            "agents_created": sum(1 for e in _trace_entries if e["event"].startswith("Agent CREATED")),
            "llm_calls": sum(1 for e in _trace_entries if "HTTP Request" in str(e.get("data", {}))),
            "serp_api_calls": sum(1 for e in _trace_entries if e["category"] == "API_CALL"),
            "serp_api_remaining": 250 - sum(1 for e in _trace_entries if e["category"] == "API_CALL"),
        },
        "result": {
            "convergence_success": is_success,
            "total_cost": converged.total_group_flight_cost if hasattr(converged, "total_group_flight_cost") else converged.get("total_group_flight_cost"),
            "failure_reason": converged.failure_reason if hasattr(converged, "failure_reason") else converged.get("failure_reason"),
        },
    }

    trace("REPORT", "simulation", "Final execution report", data=report)


# ── 6. Main ──────────────────────────────────────────────────────────────

async def main():
    print("=" * 80)
    print("MACI v2 — COMPREHENSIVE E2E SIMULATION")
    print(f"Simulation ID: {SIMULATION_ID}")
    print(f"Started: {datetime.utcnow().isoformat()}Z")
    print("=" * 80)

    try:
        # Phase 1: Setup
        setup_environment()

        # Phase 2: Build scenario
        scenario = build_scenario()

        # Phase 3: Execute orchestrator with full tracing
        final_state = await run_orchestrator(scenario)

        # Phase 4: Generate report
        generate_report(scenario, final_state)

    except Exception as e:
        trace("ERROR", "simulation", f"FATAL: {e}", data={
            "traceback": traceback.format_exc(),
        })
    finally:
        # Always save the trace, even on failure
        save_trace()


if __name__ == "__main__":
    # Suppress noisy Azure SDK logs, keep only our trace + maci logs
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    logging.getLogger("maci").setLevel(logging.INFO)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    asyncio.run(main())
