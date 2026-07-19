"""
Rally Payment Service — Main FastAPI Application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.payments import router as payments_router
from app.routes.webhooks import router as webhooks_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rally.payment")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown."""
    logger.info("Starting Rally Payment Service...")
    yield
    logger.info("Shutting down Rally Payment Service...")


app = FastAPI(
    title="Rally Payment Service",
    description="Manages escrow, Stripe/Razorpay integrations, and split payments.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(payments_router)
app.include_router(webhooks_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "payment-service"}
