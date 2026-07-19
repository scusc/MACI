"""
Rally API Gateway — Authentication Middleware.
"""

import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from maci_core.core.security import verify_token

logger = logging.getLogger("rally.gateway.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude health check and public webhooks
        if request.url.path.startswith("/health") or "/webhooks/" in request.url.path:
            return await call_next(request)

        # Pass-through for auth routes
        if "/api/v1/auth/" in request.url.path:
            return await call_next(request)

        # Validate JWT
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid token"})
        
        try:
            token = auth_header.split(" ")[1]
            payload = verify_token(token, expected_type="access")
            request.state.user = payload
        except Exception as e:
            return JSONResponse(status_code=401, content={"detail": f"Invalid token: {str(e)}"})
        
        response = await call_next(request)
        return response
