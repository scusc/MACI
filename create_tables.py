import asyncio
import urllib.parse
import sys
import os

# Add service paths to sys.path
sys.path.append(os.path.join(os.getcwd(), 'maci-core'))
sys.path.append(os.path.join(os.getcwd(), 'payment-service'))

from sqlalchemy.ext.asyncio import create_async_engine
from maci_core.database import Base as CoreBase

# Import core models
from maci_core.models.user import User, PsychometricProfile
from maci_core.models.connection import MatchConnection, ChatMessage
from maci_core.models.moderation import Report, Ban
from maci_core.models.meetup import Meetup, MeetupMember
from maci_core.models.asset import Asset
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember
from maci_core.models.insurance import InsurancePolicy
from maci_core.models.skill_swap import PodSkill, SkillSwapRequest


# Import payment models
from app.models.models import Base as PaymentBase, Payment
from sqlalchemy import text

async def main():
    password = 'p)Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'
    encoded = urllib.parse.quote_plus(password)
    db_url = f"postgresql+asyncpg://maciadmin:{encoded}@psql2-maci-dev.postgres.database.azure.com:5432/rally?ssl=require"
    
    engine = create_async_engine(db_url, echo=False)
    print("Enabling pgvector and geospatial extensions...")
    for ext_sql in [
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "CREATE EXTENSION IF NOT EXISTS cube;",
        "CREATE EXTENSION IF NOT EXISTS earthdistance;"
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(ext_sql))
        except Exception as e:
            print(f"Extension notice ({ext_sql.strip()}):", e)

    async with engine.begin() as conn:
        print("Creating missing tables for Slice...")
        await conn.run_sync(CoreBase.metadata.create_all)
        await conn.run_sync(PaymentBase.metadata.create_all)
    print("Tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
