import asyncio
import urllib.parse
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'maci-core'))
sys.path.append(os.path.join(os.getcwd(), 'group-service'))

from sqlalchemy.ext.asyncio import create_async_engine
from maci_core.models.base import Base
import app.models.models

async def main():
    password = 'p)Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'
    encoded = urllib.parse.quote_plus(password)
    db_url = f"postgresql+asyncpg://maciadmin:{encoded}@psql2-maci-dev.postgres.database.azure.com:5432/rally?ssl=require"
    
    engine = create_async_engine(db_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created!")

if __name__ == "__main__":
    asyncio.run(main())
