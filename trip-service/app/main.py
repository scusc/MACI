"""
MACI Trip Microservice Entrypoint.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from maci_core.config import settings
from maci_core.core.exceptions import MACIError
from app.api.trips import router as trips_router
from app.api.rally import router as rally_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Trip Service")
    yield
    print("👋 Shutting down Trip Service")

app = FastAPI(
    title="MACI Trip Service",
    lifespan=lifespan,
    docs_url="/docs",
)

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

app.include_router(trips_router, prefix=settings.API_PREFIX)
app.include_router(rally_router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "trip-service"}
