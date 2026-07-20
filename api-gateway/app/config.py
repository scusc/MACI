"""
Rally API Gateway — Configuration.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Downstream Services
    group_service_url: str = os.getenv("GROUP_SERVICE_URL", "http://group-service")
    payment_service_url: str = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service")
    notification_service_url: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service")
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth-service")
    asset_service_url: str = os.getenv("ASSET_SERVICE_URL", "http://asset-service")
    trip_service_url: str = os.getenv("TRIP_SERVICE_URL", "http://trip-service")

    # JWT Auth
    jwt_secret: str = os.getenv("JWT_SECRET", "mock_secret")
    jwt_algorithm: str = "HS256"

    model_config = {"env_prefix": "RALLY_GATEWAY_"}


settings = Settings()
