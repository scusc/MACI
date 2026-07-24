"""
MACI Backend Configuration.

All settings are loaded from environment variables with sensible defaults
for local development. In production, these are injected via Docker env.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "MACI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://maci:maci_dev_password@localhost:5432/maci",
        description="Async PostgreSQL connection string",
    )

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and pub/sub",
    )
    FLIGHT_CACHE_TTL_SECONDS: int = Field(
        default=900,  # 15 minutes
        description="TTL for cached flight search results",
    )

    # ── Auth & Security ──────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32-for-vault",
        description="Master secret key for Data Vault encryption (PBKDF2/Fernet). MUST be changed.",
    )
    JWT_SECRET_KEY: str = Field(
        default="CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32",
        description="Secret key for JWT signing. MUST be changed in production.",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Stripe (Identity & Fintech) ──────────────────────────────────
    STRIPE_SECRET_KEY: str = Field(
        default="",
        description="Stripe Secret API Key for Identity KYC and Connect Escrow.",
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="",
        description="Stripe Webhook signing secret.",
    )

    # ── LLM ──────────────────────────────────────────────────────────
    LLM_MODEL: str = Field(
        default="gemini/gemini-2.0-flash",
        description="LiteLLM model identifier. Change to 'gpt-4o-mini' or 'claude-sonnet' as needed.",
    )
    LLM_MAX_TOKENS: int = Field(
        default=2000,
        description="Hard cap on tokens per LLM call to protect costs.",
    )
    LLM_MAX_RETRIES: int = Field(
        default=3,
        description="Instructor auto-retries on schema validation failures.",
    )
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google AI Studio API key for Gemini models.",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key (alternative provider).",
    )
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key (alternative provider).",
    )

    # ── Flight Providers ─────────────────────────────────────────────
    AMADEUS_CLIENT_ID: str = Field(
        default="",
        description="Amadeus API client ID.",
    )
    AMADEUS_CLIENT_SECRET: str = Field(
        default="",
        description="Amadeus API client secret.",
    )
    AMADEUS_ENVIRONMENT: str = Field(
        default="test",
        description="'test' for sandbox, 'production' for live data.",
    )
    DUFFEL_ACCESS_TOKEN: str = Field(
        default="",
        description="Duffel API access token.",
    )
    SERPAPI_API_KEY: str = Field(
        default="",
        description="SerpAPI key for Google Flights scraping fallback.",
    )

    # ── Negotiation Engine ───────────────────────────────────────────
    DEFAULT_MAX_ARRIVAL_SPREAD_MINUTES: int = Field(
        default=120,
        description="Default Δt_max: maximum minutes between first and last cluster arrival.",
    )
    DEFAULT_FRICTION_WEIGHT_CENTS: int = Field(
        default=2500,
        description="Default W_f: cost penalty per hour of layover, in cents ($25/hr).",
    )
    MAX_NEGOTIATION_ROUNDS: int = Field(
        default=10,
        description="Hard limit on negotiation rounds before failing gracefully.",
    )
    PROPOSAL_TTL_MINUTES: int = Field(
        default=60,
        description="How long a consensus proposal remains valid before revalidation.",
    )

    # ── CORS ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins for the frontend.",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Singleton instance — import this everywhere
settings = Settings()
