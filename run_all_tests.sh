#!/bin/bash
echo "Waiting for group-service to restart..."
kubectl rollout status deployment/group-service -n rally --timeout=120s

echo "Checking env inside pod..."
kubectl exec -it deployment/group-service -n rally -- env | grep DATABASE_URL

echo "Running DB migration inside pod..."
kubectl exec -it deployment/group-service -n rally -- /bin/bash -c "pip install asyncpg && python -c \"
import asyncio
import asyncpg
import os
import ssl

async def main():
    db_url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg', 'postgresql')
    print('Connecting to DB...')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = await asyncpg.connect(db_url, ssl=ctx)
    sql = '''ALTER TABLE rally_users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);'''
    await conn.execute(sql)
    print('Migration applied successfully!')
    await conn.close()

asyncio.run(main())
\""

echo "Running E2E tests locally..."
python3 -m pip install httpx pytest-asyncio
python3 e2e_tests/test_e2e_live.py > e2e_test_output.log 2>&1
cat e2e_test_output.log
