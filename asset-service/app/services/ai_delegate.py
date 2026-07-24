"""
AI Delegate Module — Multi-Agent Swarm for Slice

Orchestrates the "Slice Concierge Swarm" (Logistics, Experience, Culinary agents)
using LangChain and real SerpAPI tools to help users plan their trip post-booking.
"""

import os
import json
import logging
from typing import List, Dict, Any, Annotated

from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.services import serpapi_client

logger = logging.getLogger(__name__)

# --- TOOLS ---

@tool
async def fetch_flight_options(departure_id: str, arrival_id: str, date: str) -> str:
    """Use this tool to find flight options for a user."""
    logger.info(f"Logistics Agent searching flights: {departure_id} -> {arrival_id} on {date}")
    flights = await serpapi_client.search_flights(
        departure_id=departure_id, arrival_id=arrival_id, outbound_date=date, type=2
    )
    if not flights:
        return "No flights found or error occurred."
    return json.dumps(flights)

@tool
async def fetch_local_events(location: str, query: str = "events") -> str:
    """Use this tool to find concerts, festivals, or nightlife events in a specific location."""
    logger.info(f"Experience Agent searching events in {location}")
    events = await serpapi_client.search_events(query=query, location=location)
    # Serialize the AssetCreate Pydantic models to dicts for the LLM
    return json.dumps([e.model_dump() for e in events])

@tool
async def fetch_local_restaurants(location: str, query: str = "restaurants") -> str:
    """Use this tool to find restaurants catering to specific diets or vibes."""
    logger.info(f"Culinary Agent searching restaurants in {location}: {query}")
    places = await serpapi_client.search_local(query=query, location=location)
    if not places:
        return "No restaurants found."
    return json.dumps(places)


# --- AGENT SETUP ---

def get_azure_openai_client() -> AzureChatOpenAI:
    """Creates an AzureChatOpenAI client using Entra ID authentication."""
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://mock-endpoint.openai.azure.com")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    ad_token = os.environ.get("AZURE_OPENAI_AD_TOKEN")
    
    kwargs = {
        "azure_endpoint": endpoint,
        "openai_api_version": "2024-12-01-preview",
        "azure_deployment": "o3",
        "temperature": 1,
    }
    
    if ad_token:
        kwargs["azure_ad_token"] = ad_token
    elif api_key:
        kwargs["api_key"] = api_key
    else:
        # Fallback for local testing if no managed identity is set up
        kwargs["api_key"] = "mock_key"
        
    return AzureChatOpenAI(**kwargs)


# --- SWARM EXECUTION ---

async def run_concierge_swarm(
    group_chat_context: str, 
    destination: str, 
    dates: str
) -> str:
    """
    The main orchestrator for the Slice Concierge.
    It reads the group chat context and determines which agent needs to act,
    then executes the specific agent and returns the proposal to the chat.
    """
    llm = get_azure_openai_client()
    
    # 1. Logistics Agent (Flights & Transport)
    logistics_agent = create_react_agent(
        llm, 
        tools=[fetch_flight_options],
        prompt=SystemMessage(content=f"You are the Slice Logistics Agent for {destination} on {dates}. CRITICAL: If a specific user asks for a 'sub-plan' or a personal arrangement (e.g. they want a different flight than the group), you MUST generate a separate splinter itinerary addressed directly to them. Do not affect the main group's plan.")
    )
    
    # 2. Experience Agent (Events/Nightlife)
    experience_agent = create_react_agent(
        llm,
        tools=[fetch_local_events],
        prompt=SystemMessage(content=f"You are the Slice Experience Agent for {destination}. CRITICAL: If an individual user asks for a splinter plan (e.g., they want to go to a museum while the group goes to the beach), you MUST generate a distinct sub-itinerary scoped ONLY to that user. Address them directly.")
    )
    
    # 3. Culinary Agent (Food/Dining)
    culinary_agent = create_react_agent(
        llm,
        tools=[fetch_local_restaurants],
        prompt=SystemMessage(content=f"You are the Slice Culinary Agent for {destination}. CRITICAL: If an individual user has a distinct dietary request that branches from the main group, generate a specific sub-reservation plan just for them.")
    )
    
    # Simple Orchestrator Logic: Look at the last message to decide which agent to trigger
    # In a production LangGraph, this would be a routing node.
    prompt = group_chat_context.lower()
    
    if "flight" in prompt or "fly" in prompt or "airport" in prompt:
        logger.info("Routing to Logistics Agent")
        result = await logistics_agent.ainvoke({"messages": [HumanMessage(content=group_chat_context)]})
        return result["messages"][-1].content
        
    elif "eat" in prompt or "food" in prompt or "dinner" in prompt or "restaurant" in prompt:
        logger.info("Routing to Culinary Agent")
        result = await culinary_agent.ainvoke({"messages": [HumanMessage(content=group_chat_context)]})
        return result["messages"][-1].content
        
    else:
        # Default to Experience/Events
        logger.info("Routing to Experience Agent")
        result = await experience_agent.ainvoke({"messages": [HumanMessage(content=group_chat_context)]})
        return result["messages"][-1].content