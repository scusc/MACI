"""
Rally Notification Service — AI Nudge Engine.
Uses Azure OpenAI to generate context-aware, personalized nudges for group trips.
"""

import logging
import os
from pathlib import Path

from app.config import settings

logger = logging.getLogger("rally.notification.nudge")

# Load prompt template
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "nudge_agent.md"
with open(PROMPT_PATH, "r") as f:
    PROMPT_TEMPLATE = f.read()


class MockAzureOpenAI:
    """Mock for local development without actual OpenAI API calls."""
    @staticmethod
    async def generate(prompt: str) -> str:
        # Simple extraction of context for mock response
        # In production, this would call the actual LLM
        return "Hey there! 4 out of 6 of your crew have locked in. Flights from your city are trending up slightly. Lock your spot in before the weekend so the trip can happen!"


async def generate_nudge(
    trip_title: str,
    destination: str,
    progress_pct: int,
    threshold_pct: int,
    member_name: str,
    member_status: str,
    origin_airport: str,
    price_trend: str
) -> str:
    """
    Generate a personalized nudge using the LLM.
    """
    prompt = PROMPT_TEMPLATE.format(
        trip_title=trip_title,
        destination=destination,
        progress_pct=progress_pct,
        threshold_pct=threshold_pct,
        member_name=member_name,
        member_status=member_status,
        origin_airport=origin_airport,
        price_trend=price_trend
    )

    logger.info("Generating AI nudge for %s (Trip: %s)", member_name, trip_title)
    
    # Use mock for now to save API costs during dev/tests
    # In prod: client = AsyncAzureOpenAI(...)
    # response = await client.chat.completions.create(...)
    response_text = await MockAzureOpenAI.generate(prompt)
    
    return response_text
