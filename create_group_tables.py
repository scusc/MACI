"""
Create all group-service database tables.
Run: python3 create_group_tables.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'maci-core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'group-service'))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://maciadmin:p%2BY%5Bp2A.zuj.7efn5QT%3DYiHx7-NBZ%5DD%24@psql3-maci-dev.postgres.database.azure.com:5432/rally?ssl=require"
)

async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(DATABASE_URL, echo=False)

    # Import all models so their metadata is registered
    from app.models.models import Base

    print("Creating group-service tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All group-service tables created successfully!")

    # List created tables
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        tables = [row[0] for row in result]
        print(f"\nTables in DB ({len(tables)} total):")
        for t in tables:
            print(f"  - {t}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
