import logging
from sqlalchemy.ext.asyncio import AsyncSession
from maci_core.models.user import User

logger = logging.getLogger(__name__)

class KarmaService:
    """
    Manages the algorithmic scoring of users based on their behavior in pools.
    """
    
    @staticmethod
    async def deduct_for_late_cancellation(db: AsyncSession, user: User):
        """
        Deducts 5 points if a user cancels AFTER the Escrow pool has been locked.
        This strongly disincentivizes abandoning a pool and ruining the trip for others.
        """
        logger.info(f"Deducting karma for late cancellation: User {user.id}")
        user.karma_score = max(0.0, user.karma_score - 5.0)
        await db.commit()
        return user.karma_score

    @staticmethod
    async def reward_for_successful_trip(db: AsyncSession, user: User):
        """
        Rewards 1 point for successfully completing a trip without a vibe check failure.
        """
        logger.info(f"Rewarding karma for successful trip: User {user.id}")
        # Cap at 10.0 (maximum karma)
        user.karma_score = min(10.0, user.karma_score + 1.0)
        await db.commit()
        return user.karma_score

karma_engine = KarmaService()
