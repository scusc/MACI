"""
Rally Notification Service — Main FastAPI Application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.services.nudge_engine import generate_nudge
from app.services.price_monitor import run_price_monitor_job
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rally.notification")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown."""
    logger.info("Starting Rally Notification Service...")
    monitor_task = asyncio.create_task(run_price_monitor_job())
    yield
    logger.info("Shutting down Rally Notification Service...")
    monitor_task.cancel()


app = FastAPI(
    title="Rally Notification Service",
    description="Handles AI nudges, price alerts, and communications.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NudgeRequest(BaseModel):
    trip_title: str
    destination: str
    progress_pct: int
    threshold_pct: int
    member_name: str
    member_status: str
    origin_airport: str
    price_trend: str

@app.post("/api/v1/nudges/generate", tags=["nudges"])
async def generate_member_nudge(req: NudgeRequest):
    """Generate an AI nudge for a specific member."""
    message = await generate_nudge(
        trip_title=req.trip_title,
        destination=req.destination,
        progress_pct=req.progress_pct,
        threshold_pct=req.threshold_pct,
        member_name=req.member_name,
        member_status=req.member_status,
        origin_airport=req.origin_airport,
        price_trend=req.price_trend
    )
    return {"message": message}

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "notification-service"}
