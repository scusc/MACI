"""
Rally Group Service — Main FastAPI Application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.trips import router as trips_router
from app.routes.organizer import router as organizer_router
from app.routes.auth import router as auth_router
from maci_core.database import engine, Base
from maci_core.events.bus import bus_manager
from maci_core.events.schemas import PaymentIntentAuthorizedEvent
import app.models.models  # Import all models so metadata binds them

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rally.group")


async def handle_payment_authorized(event_data: dict):
    from app.routes.trips import mark_member_paid
    from maci_core.database import async_session_factory
    import uuid
    
    try:
        event = PaymentIntentAuthorizedEvent(**event_data)
        logger.info(f"Received payment.authorized event for member {event.member_id}")
        
        async with async_session_factory() as db:
            await mark_member_paid(
                trip_id=uuid.UUID(event.trip_id),
                member_id=uuid.UUID(event.member_id),
                db=db
            )
    except Exception as e:
        logger.error(f"Error handling payment.authorized: {e}")

async def start_service_bus_listeners():
    logger.info("Starting Service Bus listener for PaymentIntentAuthorizedEvent")
    await bus_manager.listen_to_subscription(
        topic_name="payment.authorized",
        subscription_name="group_service_sub",
        message_handler=handle_payment_authorized
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown."""
    logger.info("Starting Rally Group Service...")
    
    # Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    import asyncio
    sb_task = asyncio.create_task(start_service_bus_listeners())
    yield
    logger.info("Shutting down Rally Group Service...")
    sb_task.cancel()


app = FastAPI(
    title="Rally Group Service",
    description="Manages trips, members, and commitments for Rally platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(trips_router)
app.include_router(organizer_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "group-service"}
