"""
MACI Auth Microservice Entrypoint.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from maci_core.config import settings
from maci_core.core.exceptions import MACIError
from app.api.auth import router as auth_router
from app.api.webhooks import router as webhooks_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Auth Service")
    yield
    print("👋 Shutting down Auth Service")

from maci_core.observability import setup_observability

app = FastAPI(
    title="Slice Auth Service",
    lifespan=lifespan,
    docs_url="/docs",
)

# Inject Prometheus metrics and OpenTelemetry tracing
setup_observability(app, "auth-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(webhooks_router, prefix=settings.API_PREFIX)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth-service"}
