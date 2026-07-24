#!/bin/bash
set -e

echo "=== 🚀 Rally CI/CD Local Verification Suite ==="

echo "1. Verifying Python Backend Compilation..."
python3 -m py_compile $(find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*")
echo "✅ All Python microservices compiled cleanly!"

echo "2. Verifying Angular 22 Frontend Types..."
cd frontend
npm ci --silent
npx tsc --noEmit
cd ..
echo "✅ Angular TypeScript frontend verified cleanly!"

echo "3. Running Database Schema Migration..."
python3 -c "
import asyncio, os, urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('Skipping live DB schema update (DATABASE_URL not set).')
        return
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT \'free\';'))
        await conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP WITH TIME ZONE;'))
        print('DB migration applied cleanly!')
    await engine.dispose()

asyncio.run(main())
"

echo "=== 🎉 All Rally CI/CD checks completed successfully! ==="
