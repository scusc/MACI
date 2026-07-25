"""
Rally Group Service — Main FastAPI Application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from maci_core.database import engine, Base
import app.models.models  # Import all models so metadata binds them

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rally.group")


async def handle_payment_authorized(event_data: dict):
    pass

async def start_service_bus_listeners():
    try:
        from maci_core.events.bus import bus_manager
        logger.info("Starting Service Bus listener for PaymentIntentAuthorizedEvent")
        await bus_manager.listen_to_subscription(
            topic_name="payment.authorized",
            subscription_name="group_service_sub",
            message_handler=handle_payment_authorized
        )
    except Exception as e:
        logger.warning(f"Service Bus listener skipped: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown."""
    logger.info("Starting Rally Group Service...")
    
    # Create DB tables if DB connected
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"Database table sync skipped: {e}")
        
    import asyncio
    sb_task = asyncio.create_task(start_service_bus_listeners())
    yield
    logger.info("Shutting down Rally Group Service...")
    sb_task.cancel()


app = FastAPI(
    title="Rally Group Service",
    description="Manages trips, members, and commitments for Rally platform.",
    redirect_slashes=False,
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
from app.routes.profile import router as profile_router
from app.routes.chat import router as chat_router
from app.routes.handshake import router as handshake_router
from app.routes.meetups import router as meetups_router
from app.routes.skill_swap import router as skill_swap_router
from app.routes.trips import router as trips_router
from app.routes.organizer import router as organizer_router

app.include_router(trips_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(handshake_router, prefix="/api/v1")
app.include_router(meetups_router, prefix="/api/v1")
app.include_router(skill_swap_router, prefix="/api/v1")
app.include_router(organizer_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "group-service"}
