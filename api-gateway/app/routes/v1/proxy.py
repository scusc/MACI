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

@router.api_route("/chat/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_chat(request: Request, path: str):
    """Proxy chat-related requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/payments/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_payments(request: Request, path: str):
    """Proxy payment-related requests to payment-service."""
    return await proxy_request(request, settings.payment_service_url)

@router.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_auth(request: Request, path: str):
    """Proxy auth and KYC requests to auth-service."""
    return await proxy_request(request, settings.auth_service_url)

@router.api_route("/assets/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_assets(request: Request, path: str):
    """Proxy assets and webhooks to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/pools/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_pools(request: Request, path: str):
    """Proxy pools to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/insurance/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_insurance(request: Request, path: str):
    """Proxy insurance to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/vendor/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_vendor(request: Request, path: str):
    """Proxy vendor analytics to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/organizer/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_organizer(request: Request, path: str):
    """Proxy organizer requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/handshake/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_handshake(request: Request, path: str):
    """Proxy mutual identity handshake requests to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/meetups/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_meetups(request: Request, path: str):
    """Proxy local micro-commitment meetups to group-service."""
    return await proxy_request(request, settings.group_service_url)

@router.api_route("/subscription/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_subscription(request: Request, path: str):
    """Proxy Trust Passport subscription requests to auth-service."""
    return await proxy_request(request, settings.auth_service_url)

@router.api_route("/matching/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_matching(request: Request, path: str):
    """Proxy psychometric AI matching requests to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/travel/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_travel(request: Request, path: str):
    """Proxy real travel API requests to asset-service."""
    return await proxy_request(request, settings.asset_service_url)

@router.api_route("/plan", methods=["POST"])
async def proxy_plan(request: Request):
    """Proxy AI planning requests to trip-service."""
    return await proxy_request(request, settings.trip_service_url)

