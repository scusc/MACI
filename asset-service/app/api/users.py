import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from maci_core.database import get_db
from maci_core.models.user import User
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember

router = APIRouter(prefix="/users", tags=["Users Activity Dashboard"])

@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public User Activity Dashboard.
    Returns community tenure (days since signup) and total completed trips.
    """
    u_stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(u_stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Calculate Tenure
    if user.created_at:
        delta = datetime.now(timezone.utc) - user.created_at
        tenure_days = delta.days
    else:
        tenure_days = 0
        
    # Calculate Completed Trips
    # A user has completed a trip if they are an approved member of a pool that is 'completed'
    trips_stmt = select(func.count(PoolMember.id)).join(Pool, PoolMember.pool_id == Pool.id).where(
        PoolMember.user_id == uuid.UUID(user_id),
        PoolMember.status == "approved",
        Pool.status == "completed"
    )
    completed_trips = (await db.execute(trips_stmt)).scalar() or 0
    
    return {
        "user_id": str(user.id),
        "username": user.email.split("@")[0] if user.email else "User",
        "tenure_days": tenure_days,
        "completed_trips": completed_trips,
        "karma_score": user.karma_score,
        "is_identity_verified": user.kyc_status == "verified"
    }
