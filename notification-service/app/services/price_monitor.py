"""
Rally Notification Service — Price Monitoring Background Job.
"""

import logging
import asyncio
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
# Note: we need to setup a small db connection in notification service if it touches the DB directly,
# or it can call group-service APIs. For microservices, calling group-service is better.
# For now, since they share the same physical DB during development, we'll just mock the behavior.

logger = logging.getLogger("rally.notification.price_monitor")


async def run_price_monitor_job():
    """
    Background job that runs periodically to check for price drops/spikes.
    If a significant change is detected, it triggers a price alert nudge.
    """
    logger.info("Starting Price Monitor Job...")
    
    # 1. Fetch all active trips in 'collecting' status
    # 2. For each trip, get the origins
    # 3. Call trip-service /estimate endpoint to get current prices
    # 4. Compare with historical prices in `price_snapshots`
    # 5. If change > 5%, send an alert to all members using Nudge Engine
    
    # Mocking execution loop
    while True:
        try:
            # logger.info("Running price check cycle...")
            # Do work
            pass
        except Exception as e:
            logger.error("Error in price monitor job: %s", str(e))
        
        # Run every 6 hours (mocked to sleep 1 hr for dev)
        await asyncio.sleep(3600)
