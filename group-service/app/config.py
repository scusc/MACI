"""
Rally Group Service — Configuration.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database & Cache
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://rally:rally@localhost:5432/rally"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Service URLs (inter-service communication)
    payment_service_url: str = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")
    trip_service_url: str = os.getenv("TRIP_SERVICE_URL", "http://localhost:8010")
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8003")

    # Platform fee (basis points: 300 = 3.0%)
    platform_fee_bps: int = int(os.getenv("PLATFORM_FEE_BPS", "300"))

    # Invite code length
    invite_code_length: int = 8

    model_config = {"env_prefix": "RALLY_"}


settings = Settings()
