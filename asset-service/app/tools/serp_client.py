"""
SerpAPI Client — Unified wrapper for all SerpAPI engines.

This module provides a single entry point for all SerpAPI calls used by MACI.
It handles:
  - API key retrieval from Azure Key Vault (production) or env var (dev)
  - Request counting for budget tracking (250 request limit)
  - Mock mode for development (returns cached JSON, zero API calls)
  - Structured error handling
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Optional

from serpapi import GoogleSearch

logger = logging.getLogger("maci.serp_client")

# ── Mock Data Directory ────────────────────────────────────────────────
# In mock mode, we load pre-saved JSON responses instead of hitting the API.
# This lets us develop the full pipeline without burning API credits.
MOCK_DIR = Path(__file__).parent / "mock_data"


class SerpAPIBudgetExhausted(Exception):
    """Raised when the API call budget has been exceeded."""
    pass


class SerpClient:
    """
    Unified SerpAPI client with budget tracking and mock mode.

    Usage:
        client = SerpClient()                    # Real mode
        client = SerpClient(mock_mode=True)      # Mock mode (no API calls)
        result = client.search("google_flights", {"departure_id": "SFO", ...})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        mock_mode: bool = False,
        budget_limit: int = 250,
    ):
        self.mock_mode = mock_mode or os.getenv("MACI_MOCK_MODE", "false").lower() == "true"
        self.budget_limit = budget_limit
        self._call_count = 0

        if not self.mock_mode:
            # Priority: explicit key > env var > Azure Key Vault (future)
            self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
            if not self.api_key:
                raise RuntimeError(
                    "SERPAPI_API_KEY not found. Set it as an env var or pass it explicitly. "
                    "In production, it is read from Azure Key Vault."
                )
        else:
            self.api_key = "mock-key-not-used"
            logger.info("SerpClient initialized in MOCK MODE — no API calls will be made")

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
        if self.mock_mode:
            return self._load_mock(engine, params)

        if self._call_count >= self.budget_limit:
            raise SerpAPIBudgetExhausted(
                f"Budget exhausted: {self._call_count}/{self.budget_limit} calls used. "
                "Switch to mock mode or increase budget."
            )

        # Build the full params dict
        full_params = {
            "engine": engine,
            "api_key": self.api_key,
            **params,
        }

        logger.info(
            "SerpAPI call #%d/%d — engine=%s, params=%s",
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

    def _load_mock(self, engine: str, params: dict[str, Any]) -> dict[str, Any]:
        """Load a cached mock response for development."""
        # Build a deterministic filename from engine + key params
        key_parts = [engine]
        for k in sorted(params.keys()):
            if k not in ("api_key",):
                key_parts.append(f"{k}={params[k]}")
        mock_key = "__".join(key_parts)

        # Try exact match first, then fall back to engine-level default
        mock_file = MOCK_DIR / f"{mock_key}.json"
        if not mock_file.exists():
            mock_file = MOCK_DIR / f"{engine}_default.json"

        if mock_file.exists():
            logger.info("Loading mock response from %s", mock_file.name)
            return json.loads(mock_file.read_text())

        logger.warning("No mock data found for %s. Returning empty result.", engine)
        return {"search_metadata": {"status": "mock_empty"}, "error": "No mock data available"}

    def save_as_mock(self, engine: str, params: dict[str, Any], response: dict[str, Any]) -> Path:
        """
        Save a real API response as mock data for future development.
        Call this after a real search to build your mock library.
        """
        MOCK_DIR.mkdir(parents=True, exist_ok=True)
        key_parts = [engine]
        for k in sorted(params.keys()):
            if k not in ("api_key",):
                key_parts.append(f"{k}={params[k]}")
        mock_key = "__".join(key_parts)
        mock_file = MOCK_DIR / f"{mock_key}.json"
        mock_file.write_text(json.dumps(response, indent=2, ensure_ascii=False))
        logger.info("Saved mock response to %s", mock_file)
        return mock_file
