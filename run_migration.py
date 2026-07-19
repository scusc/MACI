import asyncio
import asyncpg
import urllib.parse
import ssl

async def main():
    password = 'p)Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'
    encoded = urllib.parse.quote_plus(password)
    db_url = f"postgresql://maciadmin:{encoded}@psql2-maci-dev.postgres.database.azure.com:5432/rally?sslmode=require"
    print("Connecting to DB...")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(db_url, ssl=ctx)
    print("Executing SQL...")
    
    with open("db-migrations/004_auth_passwords.sql") as f:
        sql = f.read()
    
    await conn.execute(sql)
    print("Migration applied successfully!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
