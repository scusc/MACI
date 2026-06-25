"""
AI Delegate Module (LangChain + Azure OpenAI)

This module handles the actual LLM interaction. It takes a cluster of travelers,
constructs a structured prompt containing their constraints, and uses LangChain
to query Azure OpenAI (via APIM).

The LLM is asked to generate flight parameters that satisfy all travelers in the cluster,
balancing the Friction Exchange Rate (cost vs layover pain).
"""

from typing import List, Dict, Any
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from azure.identity import DefaultAzureCredential
import os

from app.services.orchestrator import Cluster

# In a real app, these come from environment variables injected by ConfigMap
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://apim-maci-dev.azure-api.net")
AZURE_OPENAI_API_VERSION = "2024-05-13"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"

def get_azure_openai_client() -> AzureChatOpenAI:
    """
    Creates an AzureChatOpenAI client using Entra ID authentication.
    No API keys are used! It gets a token from the AKS Workload Identity
    and passes it to APIM/OpenAI.
    """
    # 1. Get an Entra ID token using the AKS managed identity
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    # 2. Initialize LangChain with the token
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        api_key=token.token,  # We pass the Entra ID JWT as the "api_key"
        temperature=0.2, # Low temperature for deterministic reasoning
    )

async def negotiate_cluster_itinerary(cluster: Cluster) -> Dict[str, Any]:
    """
    Takes a single cluster of travelers and asks the LLM to negotiate the best flight window.
    """
    llm = get_azure_openai_client()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an autonomous AI delegate representing a cluster of enterprise travelers 
        all departing from {origin_airport}.
        
        Your job is to evaluate their constraints and propose a single flight departure window 
        that minimizes the 'Friction Exchange Rate' (total cost + layover pain) while ensuring 
        all travelers arrive at the destination within the global convergence window.
        
        Output your proposal as a JSON object containing:
        - proposed_departure_window_start (ISO8601)
        - proposed_departure_window_end (ISO8601)
        - max_acceptable_price_usd (int)
        - accepted_layover_penalty_hours (int)
        - reasoning (brief explanation)
        """),
        ("user", "Here are the constraints for the travelers in this cluster:\n\n{constraints}")
    ])

    # Format the traveler constraints into a readable string
    constraints_str = ""
    for t in cluster.travelers:
        constraints_str += f"Traveler {t.traveler_id}: Earliest Departure: {t.earliest_departure}, Latest Arrival: {t.latest_arrival}\n"

    chain = prompt | llm

    # Execute the LLM call
    response = await chain.ainvoke({
        "origin_airport": cluster.origin_airport,
        "constraints": constraints_str
    })

    # In production, we would use LangChain's StructuredOutputParser to validate the JSON.
    return {"raw_response": response.content}
