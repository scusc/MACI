"""
MACI v2: End-to-End Test Script

This script tests the entire LangGraph Map-Reduce Orchestrator hitting REAL APIS.
It disables Mock Mode, fetches the SerpAPI key from Azure Key Vault,
authenticates to Azure OpenAI using DefaultAzureCredential, and triggers
the flight convergence algorithm for a multi-origin trip.
"""

import asyncio
import os
import json
import logging
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Set up logging to see what the agents are doing
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("maci_test")

# ── 1. Environment Setup ──────────────────────────────────────────────────
# Disable mock mode so we hit the REAL SerpAPI!
os.environ["MACI_MOCK_MODE"] = "false"

# The Direct Azure OpenAI Endpoint (bypassing APIM for local testing since APIM needs Terraform updates for the new gpt-5.6-luna deployment)
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://oai-maci-dev-de7cc.openai.azure.com/"

def setup_secrets():
    """Fetch the SerpAPI key securely from Azure Key Vault for the local test."""
    logger.info("Authenticating to Azure to fetch secrets...")
    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url="https://kv-maci-dev-123.vault.azure.net", credential=credential)
        secret = client.get_secret("serpapi-key")
        os.environ["SERPAPI_API_KEY"] = secret.value
        logger.info("Successfully loaded SERPAPI_API_KEY from Key Vault.")
    except Exception as e:
        logger.error(f"Failed to fetch secret from Key Vault: {e}")
        # Fallback to local env var if already set
        if not os.getenv("SERPAPI_API_KEY"):
            raise RuntimeError("Cannot proceed without SERPAPI_API_KEY")

# ── 2. The Scenario ───────────────────────────────────────────────────────
# We have 3 travelers converging on Barcelona (BCN) for a weekend trip.
# Two are flying from San Francisco (SFO) and one from New York (JFK).
# We want the orchestrator to map-reduce the searches and converge them.

test_outbound_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

test_travelers = [
    {
        "traveler_id": "T1_Alice",
        "origin_airport": "SFO",
        "earliest_departure": f"{test_outbound_date} 06:00",
        "latest_arrival": f"{test_outbound_date} 23:59",
        "budget_flights_usd": 1200
    },
    {
        "traveler_id": "T2_Bob",
        "origin_airport": "SFO",
        "earliest_departure": f"{test_outbound_date} 08:00",
        "latest_arrival": f"{test_outbound_date} 23:59",
        "budget_flights_usd": 1200
    },
    {
        "traveler_id": "T3_Carol",
        "origin_airport": "JFK",
        "earliest_departure": f"{test_outbound_date} 06:00",
        "latest_arrival": f"{test_outbound_date} 23:59",
        "budget_flights_usd": 800
    }
]

initial_state = {
    "destination": "Barcelona, Spain",
    "outbound_date": test_outbound_date,
    "return_date": None,
    "travelers": test_travelers,
    "flight_proposals": [],
    "converged_itinerary": None,
    "hotels": [],
    "activities": [],
    "price_intelligence": ""
}

# ── 3. Execution ──────────────────────────────────────────────────────────

async def run_test():
    setup_secrets()
    
    logger.info("Starting MACI LangGraph Orchestrator...")
    logger.info(f"Target: Converging {len(test_travelers)} travelers from SFO and JFK to BCN on {test_outbound_date}")
    
    from app.services.orchestrator import build_orchestrator_graph
    
    graph = build_orchestrator_graph()
    
    logger.info("\n--- EXECUTING GRAPH ---")
    
    # We use ainvoke to run the async graph
    try:
        final_state = await graph.ainvoke(initial_state)
        
        logger.info("\n--- GRAPH EXECUTION COMPLETE ---")
        
        # ── 4. Results ──────────────────────────────────────────────────────
        converged = final_state.get("converged_itinerary")
        
        if not converged:
            logger.error("Convergence Node returned None!")
            return
            
        if converged.get("is_successful") if isinstance(converged, dict) else converged.is_successful:
            logger.info("✅ SUCCESS: Found a converged itinerary!")
            
            # Handle object vs dict serialization based on how LangGraph reduces state
            cost = converged.get("total_group_flight_cost") if isinstance(converged, dict) else converged.total_group_flight_cost
            win_start = converged.get("convergence_window_start") if isinstance(converged, dict) else converged.convergence_window_start
            win_end = converged.get("convergence_window_end") if isinstance(converged, dict) else converged.convergence_window_end
            flights = converged.get("selected_flights", []) if isinstance(converged, dict) else converged.selected_flights
            
            logger.info(f"Total Group Flight Cost: ${cost}")
            logger.info(f"Arrival Window (Local BCN Time): {win_start} to {win_end}")
            
            print("\nSelected Flights:")
            for f in flights:
                orig = f.get("origin_airport") if isinstance(f, dict) else f.origin_airport
                price = f.get("total_price_usd") if isinstance(f, dict) else f.total_price_usd
                print(f" - From {orig}: ${price}")
                
        else:
            reason = converged.get("failure_reason") if isinstance(converged, dict) else converged.failure_reason
            logger.warning(f"❌ CONVERGENCE FAILED: {reason}")
            
    except Exception as e:
        logger.error(f"Graph execution crashed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run_test())
