"""
Rally API Gateway — Route proxies.
"""

from fastapi import APIRouter, Request
from app.config import settings
from app.proxy import proxy_request

router = APIRouter(prefix="/api/v1")

@router.api_route("/trips/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_trips(request: Request, path: str):
    """Proxy trip-related requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/payments/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_payments(request: Request, path: str):
    """Proxy payment-related requests to payment-service."""
    return await proxy_request(request, settings.payment_service_url)

@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_auth(request: Request, path: str):
    """Proxy auth requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/organizer/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_organizer(request: Request, path: str):
    """Proxy organizer requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/plan", methods=["POST"])
async def proxy_plan(request: Request):
    """Proxy AI planning requests to trip-service."""
    return await proxy_request(request, settings.trip_service_url)
