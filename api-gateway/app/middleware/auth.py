"""
Rally API Gateway — Authentication Middleware.
"""

import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger("rally.gateway.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude health check and public webhooks
        if request.url.path.startswith("/health") or "/webhooks/" in request.url.path:
            return await call_next(request)

        # In a real implementation, we would validate JWT here:
        # auth_header = request.headers.get("Authorization")
        # if not auth_header or not auth_header.startswith("Bearer "):
        #     return JSONResponse(status_code=401, content={"detail": "Missing or invalid token"})
        # 
        # try:
        #     token = auth_header.split(" ")[1]
        #     payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        #     request.state.user = payload
        # except Exception as e:
        #     return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        
        # For this prototype, we'll just pass through
        request.state.user = {"email": "demo@rally.app"}
        
        response = await call_next(request)
        return response
