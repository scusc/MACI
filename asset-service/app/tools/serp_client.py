"""
SerpAPI Client — Unified wrapper for all SerpAPI engines.

This module provides a single entry point for all SerpAPI calls used by MACI.
It handles:
  - API key retrieval from Azure Key Vault (production) or env var (dev)
  - Request counting for budget tracking (250 request limit)
  - Structured error handling
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional

from serpapi import GoogleSearch

logger = logging.getLogger("maci.serp_client")


class SerpAPIBudgetExhausted(Exception):
    """Raised when the API call budget has been exceeded."""
    pass


class SerpClient:
    """
    Unified SerpAPI client with budget tracking. LIVE Production Mode.

    Usage:
        client = SerpClient()
        result = client.search("google_flights", {"departure_id": "SFO", ...})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        budget_limit: int = 250,
    ):
        self.budget_limit = budget_limit
        self._call_count = 0

        # Priority: explicit key > env var > Azure Key Vault (future)
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            # Forcing hard failure to ensure live integration during Phase 8
            raise RuntimeError(
                "SERPAPI_API_KEY not found. Set it as an env var or pass it explicitly."
            )

    @property
    def calls_remaining(self) -> int:
        return max(0, self.budget_limit - self._call_count)

    def search(self, engine: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a SerpAPI search.

        Args:
            engine: The SerpAPI engine name (e.g., "google_flights", "google_hotels")
            params: Engine-specific parameters (do NOT include api_key or engine)

        Returns:
            The raw JSON response as a dict.
        """
        if self._call_count >= self.budget_limit:
            raise SerpAPIBudgetExhausted(
                f"Budget exhausted: {self._call_count}/{self.budget_limit} calls used. "
            )

        # Build the full params dict
        full_params = {
            "engine": engine,
            "api_key": self.api_key,
            **params,
        }

        logger.info(
            "SerpAPI LIVE call #%d/%d — engine=%s, params=%s",
            self._call_count + 1,
            self.budget_limit,
            engine,
            {k: v for k, v in params.items() if k != "api_key"},
        )

        try:
            result = GoogleSearch(full_params).get_dict()
            self._call_count += 1
            logger.info("SerpAPI call succeeded. %d calls remaining.", self.calls_remaining)
            return result
        except Exception as e:
            logger.error("SerpAPI call failed: %s", str(e))
            raise
