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
from maci_core.models.user import User
from maci_core.models.asset import Asset
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember

# Import payment models
from app.models.models import Base as PaymentBase, Payment

async def main():
    password = 'p)Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'
    encoded = urllib.parse.quote_plus(password)
    db_url = f"postgresql+asyncpg://maciadmin:{encoded}@psql2-maci-dev.postgres.database.azure.com:5432/rally?ssl=require"
    
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        print("Dropping all existing tables...")
        await conn.run_sync(CoreBase.metadata.drop_all)
        await conn.run_sync(PaymentBase.metadata.drop_all)
        print("Creating all tables for Slice...")
        await conn.run_sync(CoreBase.metadata.create_all)
        await conn.run_sync(PaymentBase.metadata.create_all)
    print("Tables created successfully!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
