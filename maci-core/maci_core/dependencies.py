"""
Shared API Dependencies.

FastAPI dependency injection for auth, database sessions, etc.
"""

import uuid

from fastapi import Depends, Header

from maci_core.core.security import get_org_id_from_token
from maci_core.core.exceptions import TokenInvalidError


async def get_current_org_id(
    authorization: str = Header(..., description="Bearer <access_token>"),
) -> uuid.UUID:
    """
    Extract and verify the org_id from the Authorization header.

    Usage in route handlers:
        org_id: uuid.UUID = Depends(get_current_org_id)
    """
    if not authorization.startswith("Bearer "):
        raise TokenInvalidError()

    token = authorization[7:]  # Strip "Bearer "
    return get_org_id_from_token(token)
