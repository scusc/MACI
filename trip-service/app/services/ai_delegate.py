"""
AI Delegate Module — LangChain integrations for MACI v2

This module provides the execution functions for the LLM agents 
(Flight Delegate, Hotel Agent, Activity Agent) that are called by 
the LangGraph orchestrator.
"""

import os
from pathlib import Path
from typing import List, Dict, Any

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from azure.identity import DefaultAzureCredential

from maci_core.schemas.ai import DelegateResponse
from app.tools.serp_client import SerpClient
from app.tools.flight_search import create_flight_search_tool


# Use Mock Mode for local dev by default to save SerpAPI credits
MOCK_MODE = os.getenv("MACI_MOCK_MODE", "true").lower() == "true"


def get_azure_openai_client() -> AzureChatOpenAI:
    """
    Creates an AzureChatOpenAI client using Entra ID authentication.
    No API keys are used for the LLM.
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable must be set.")
        
    kwargs = {
        "azure_endpoint": endpoint,
        "openai_api_version": "2024-12-01-preview",
        "azure_deployment": "o3",
        "temperature": 1,
        "max_retries": 10,
        "max_tokens": 4000,
    }
    
    if api_key:
        kwargs["api_key"] = api_key
    else:
        # Use Entra ID (Workload Identity / Managed Identity)
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
        kwargs["azure_ad_token_provider"] = token_provider

    return AzureChatOpenAI(**kwargs)


from langgraph.prebuilt import create_react_agent

async def run_flight_delegate(
    origin: str, 
    destination: str, 
    date: str, 
    travelers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Runs the LLM agent for a single origin airport.
    Uses a React Agent to search flights, then structures the output.
    """
    import logging
    logger = logging.getLogger("maci.delegate")
    logger.info("Starting Flight Delegate for origin: %s", origin)
    
    llm = get_azure_openai_client()
    serp_client = SerpClient(mock_mode=MOCK_MODE)
    flight_tool = create_flight_search_tool(serp_client)
    
    # Load the Jinja2 prompt template
    prompt_path = Path(__file__).parent.parent / "prompts" / "flight_delegate.md"
    prompt_template = PromptTemplate.from_file(
        str(prompt_path), 
        template_format="jinja2"
    )
    
    system_prompt = prompt_template.invoke({
        "origin_airport": origin,
        "destination": destination,
        "outbound_date": date,
        "travelers": travelers
    }).to_string()
    
    # 1. Create a React Agent that can loop and call the flight search tool
    agent_executor = create_react_agent(llm, tools=[flight_tool])
    
    # 2. Run the agent to do the research
    inputs = {"messages": [
        ("system", system_prompt),
        ("user", f"Please search for flights from {origin} to {destination} on {date} and pick the top 3 options based on my constraints.")
    ]}
    
    logger.info("Executing tool-calling loop for %s...", origin)
    result = await agent_executor.ainvoke(inputs)
    final_message = result["messages"][-1].content
    
    # 3. Force the final output into our strict Pydantic schema
    logger.info("Formatting output for %s into strict schema...", origin)
    extractor = llm.with_structured_output(DelegateResponse)
    
    structured = await extractor.ainvoke([
        ("system", "Extract the flight proposals from the following text into the structured schema. Origin is " + origin),
        ("user", final_message)
    ])
    
    return structured.proposals