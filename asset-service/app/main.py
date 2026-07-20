"""
Slice Asset Service — Main FastAPI Application.
Handles the luxury asset inventory, pool creation, and Swipe feed.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from maci_core.config import settings
from maci_core.core.exceptions import MACIError
from app.api.assets import router as assets_router
from app.api.pools import router as pools_router
from app.api.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Asset Service")
    yield
    print("👋 Shutting down Asset Service")

from maci_core.observability import setup_observability

app = FastAPI(
    title="Slice Asset Service",
    lifespan=lifespan,
    docs_url="/docs",
)

# Inject Prometheus metrics and OpenTelemetry tracing
setup_observability(app, "asset-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(MACIError)
async def maci_error_handler(request, exc: MACIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.detail}},
    )

app.include_router(assets_router, prefix=settings.API_PREFIX)
app.include_router(pools_router, prefix=settings.API_PREFIX)
app.include_router(chat_router) # WebSockets do not usually take the api prefix

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "asset-service"}
