"""
Rally API Gateway — Main FastAPI Application.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.v1.proxy import router as proxy_router
from app.middleware.auth import AuthMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rally.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for startup/shutdown."""
    logger.info("Starting Rally API Gateway...")
    yield
    logger.info("Shutting down Rally API Gateway...")


app = FastAPI(
    title="Rally API Gateway",
    description="Unified API entrypoint for Rally platform services.",
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
app.add_middleware(AuthMiddleware)

# Include Routers
app.include_router(proxy_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "api-gateway"}
