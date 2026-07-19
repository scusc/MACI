"""
Rally API Gateway — Configuration.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Downstream Services
    group_service_url: str = os.getenv("GROUP_SERVICE_URL", "http://localhost:8001")
    payment_service_url: str = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8003")

    # JWT Auth
    jwt_secret: str = os.getenv("JWT_SECRET", "mock_secret")
    jwt_algorithm: str = "HS256"

    model_config = {"env_prefix": "RALLY_GATEWAY_"}


settings = Settings()
