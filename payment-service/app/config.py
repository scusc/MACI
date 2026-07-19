"""
Rally Payment Service — Configuration.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://rally:rally@localhost:5432/rally"
    )

    # Service URLs
    group_service_url: str = os.getenv("GROUP_SERVICE_URL", "http://localhost:8001")

    # Stripe
    stripe_api_key: str = os.getenv("STRIPE_API_KEY", "sk_test_mock")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_mock")

    # Razorpay
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_secret_mock")
    razorpay_webhook_secret: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_mock")

    # Platform fee
    platform_fee_bps: int = int(os.getenv("PLATFORM_FEE_BPS", "300"))

    model_config = {"env_prefix": "RALLY_PAYMENT_"}


settings = Settings()
