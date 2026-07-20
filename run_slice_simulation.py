"""
Slice End-to-End Simulation Script
"""
import asyncio
import uuid
import sys
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

# Add service paths to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'maci-core'))
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# Domain Models
from maci_core.models.user import User
from maci_core.models.asset import Asset
from maci_core.models.pool import Pool
from maci_core.models.pool_member import PoolMember
from maci_core.schemas.asset import AssetCreate
from maci_core.schemas.pool import PoolCreate

async def main():
    print("🚀 Starting Slice E2E Real-Time Simulation...\n")
    
    password = 'p)Y[p2A.zuj.7efn5QT=YiHx7-NBZ]D$'
    encoded = urllib.parse.quote_plus(password)
    db_url = f"postgresql+asyncpg://maciadmin:{encoded}@psql2-maci-dev.postgres.database.azure.com:5432/rally?ssl=require"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        # --- PHASE 1: IDENTITY GATE ---
        print("--- PHASE 1: IDENTITY GATE ---")
        host_id = uuid.uuid4()
        db.add(User(id=host_id, email="sarah@example.com", password_hash="hash", first_name="Sarah", last_name="C", is_verified=True, karma_score=4.8))
        
        joiners = [uuid.uuid4() for _ in range(3)]
        for i, j_id in enumerate(joiners):
            db.add(User(id=j_id, email=f"joiner{i}@example.com", password_hash="hash", first_name=f"Joiner{i}", last_name="X", is_verified=True, karma_score=4.5))
        await db.commit()
        print(f"✅ Created verified Host and 3 verified joiners.\n")

        # --- PHASE 2: SERPAPI INGESTION ---
        print("--- PHASE 2: SERPAPI INGESTION ---")
        sys.path.insert(0, os.path.join(os.getcwd(), 'asset-service'))
        from app.services import serpapi_client
        
        check_in = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        check_out = (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d")
        
        print("🔍 Querying live SerpAPI for 'Villas in Bali'...")
        assets_from_serpapi = await serpapi_client.search_inventory("Villas in Bali", check_in, check_out, adults=4, category="luxury")
        
        if not assets_from_serpapi:
            print("❌ SerpAPI returned nothing. Aborting.")
            return
            
        a = assets_from_serpapi[0]
        asset = Asset(title=a.title, description=a.description, asset_type=a.asset_type, category=a.category, location=a.location, total_price=a.total_price, currency=a.currency, total_slices=a.total_slices, external_reference_id=a.external_reference_id, media_urls=a.media_urls)
        db.add(asset)
        await db.flush()
        print(f"✅ Ingested live asset '{asset.title}' for ${asset.total_price}\n")

        # --- PHASE 3: POOL CREATION ---
        print("--- PHASE 3: POOL CREATION ---")
        pool = Pool(asset_id=asset.id, host_id=host_id, start_date=datetime.now(timezone.utc), end_date=datetime.now(timezone.utc), funding_deadline=datetime.now(timezone.utc), status="funding", require_vibe_check=True)
        db.add(pool)
        await db.flush()
        
        db.add(PoolMember(pool_id=pool.id, user_id=host_id, slices_committed=1, status="approved"))
        await db.commit()
        print(f"✅ Pool created by Host.\n")

        # --- PHASE 4: ESCROW PRE-AUTH ---
        print("--- PHASE 4: ESCROW PRE-AUTHORIZATION ---")
        for j_id in joiners:
            db.add(PoolMember(pool_id=pool.id, user_id=j_id, slices_committed=1, status="approved"))
            # Insert mock payment
            await db.execute(text(f"INSERT INTO slice_payments (id, pool_id, member_id, amount, platform_fee, currency, gateway, status, payment_type, created_at) VALUES ('{uuid.uuid4()}', '{pool.id}', '{j_id}', 50000, 0, 'USD', 'stripe', 'authorized', 'slice_commit', NOW())"))
        
        pool.status = "locked"
        await db.commit()
        print("✅ 3 Users swiped and authorized their cards. Pool is LOCKED for Vibe Check.\n")
        
        # --- PHASE 5: VIBE CHECK WITHDRAWAL ---
        print("--- PHASE 5: VIBE CHECK WITHDRAWAL ---")
        print("😬 A user decides to back out.")
        flaky_user = joiners[0]
        # Simulate cancel_single_authorization
        await db.execute(text(f"UPDATE slice_payments SET status = 'refunded', refunded_at = NOW() WHERE pool_id = '{pool.id}' AND member_id = '{flaky_user}'"))
        await db.commit()
        print("✅ User's authorization cancelled. Slot reopened.\n")

        # --- PHASE 6: FINAL CONFIRMATION ---
        print("--- PHASE 6: FINAL CONFIRMATION ---")
        pool.status = "confirmed"
        await db.execute(text(f"UPDATE slice_payments SET status = 'captured', escrow_released_at = NOW() WHERE pool_id = '{pool.id}' AND status = 'authorized'"))
        await db.commit()
        print(f"✅ Escrow Capture Success: Captured funds from remaining users!\n")
        
        # --- PHASE 7: MULTI-AGENT SWARM ---
        print("--- PHASE 7: THE CONCIERGE SWARM ---")
        from app.services import ai_delegate
        chat_message = "Hey team, anyone want to go out for dinner tonight in Bali?"
        print(f"💬 Group Chat: '{chat_message}'")
        
        print("🤖 Processing with LangGraph Agents...")
        try:
            response = await ai_delegate.run_concierge_swarm(chat_message, "Bali", check_in)
            print("\n🤖 AI Concierge Response:")
            print("========================")
            print(response)
            print("========================\n")
        except Exception as e:
            print(f"Agent simulation failed (possibly due to missing API keys): {e}")

    await engine.dispose()
    print("✅ E2E Simulation Complete.")

if __name__ == "__main__":
    asyncio.run(main())
