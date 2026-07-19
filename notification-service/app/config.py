"""
Rally Notification Service — Configuration.
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Downstream Services
    group_service_url: str = os.getenv("GROUP_SERVICE_URL", "http://localhost:8001")
    trip_service_url: str = os.getenv("TRIP_SERVICE_URL", "http://localhost:8010")

    # Azure OpenAI (For AI Nudges)
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "mock_endpoint")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "mock_key")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4-turbo")

    # Notification Providers
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "mock_key")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "mock_sid")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "mock_token")
    from_email: str = os.getenv("FROM_EMAIL", "hello@rally.travel")
    from_phone: str = os.getenv("FROM_PHONE", "+1234567890")

    model_config = {"env_prefix": "RALLY_NOTIF_"}

settings = Settings()
