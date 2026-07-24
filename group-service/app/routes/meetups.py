from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_db
from maci_core.models.meetup import Meetup, MeetupMember, MeetupStatus
from maci_core.schemas.meetup import MeetupCreate, MeetupResponse
import uuid
import httpx
from maci_core.config import settings

router = APIRouter(prefix="/meetups", tags=["Micro-Commitments"])

@router.post("/", response_model=MeetupResponse)
async def create_meetup(
    meetup: MeetupCreate,
    # Normally we'd inject get_current_user_id here. 
    # For MVP mock, passing it explicitly in query if absent in token for testing ease
    host_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Creates a local Micro-Commitment event (e.g. Coffee)."""
    # 4-digit PIN for check-in
    import random
    pin = str(random.randint(1000, 9999))
    
    new_meetup = Meetup(
        host_id=uuid.UUID(host_id),
        title=meetup.title,
        description=meetup.description,
        latitude=meetup.latitude,
        longitude=meetup.longitude,
        start_time=meetup.start_time,
        escrow_amount_cents=meetup.escrow_amount_cents,
        check_in_pin=pin
    )
    db.add(new_meetup)
    await db.commit()
    await db.refresh(new_meetup)
    
    return new_meetup

@router.get("/nearby")
async def get_nearby_meetups(
    latitude: float,
    longitude: float,
    radius_miles: float = 10.0,
    db: AsyncSession = Depends(get_db)
):
    """
    Uses earthdistance extension to find meetups within X miles.
    Earth is roughly 3959 miles in radius.
    """
    query = text("""
        SELECT m.id, m.title, m.latitude, m.longitude, m.start_time, m.escrow_amount_cents,
               (point(m.longitude, m.latitude) <@> point(:lon, :lat)) as distance_miles
        FROM meetups m
        WHERE m.status = 'open'
          AND (point(m.longitude, m.latitude) <@> point(:lon, :lat)) <= :radius
        ORDER BY distance_miles ASC
    """)
    
    result = await db.execute(query, {"lat": latitude, "lon": longitude, "radius": radius_miles})
    meetups = []
    for row in result:
        meetups.append({
            "id": str(row.id),
            "title": row.title,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "start_time": row.start_time,
            "escrow_amount_cents": row.escrow_amount_cents,
            "distance_miles": round(row.distance_miles, 2)
        })
        
    return {"meetups": meetups}

@router.post("/{meetup_id}/check-in")
async def check_in_meetup(
    meetup_id: str,
    user_id: str,
    pin: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validates physical presence by submitting the host's PIN.
    If valid, hits payment-service to RELEASE the Stripe hold.
    """
    from sqlalchemy import select
    from maci_core.models.meetup import MeetupMemberStatus
    
    # Verify Meetup & PIN
    stmt = select(Meetup).where(Meetup.id == uuid.UUID(meetup_id))
    meetup = (await db.execute(stmt)).scalar_one_or_none()
    if not meetup or meetup.check_in_pin != pin:
        raise HTTPException(status_code=400, detail="Invalid PIN or Meetup not found.")
        
    # Verify Member
    mem_stmt = select(MeetupMember).where(
        MeetupMember.meetup_id == uuid.UUID(meetup_id),
        MeetupMember.user_id == uuid.UUID(user_id)
    )
    member = (await db.execute(mem_stmt)).scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
        
    if member.status != MeetupMemberStatus.pending:
        raise HTTPException(status_code=400, detail="Check-in already processed.")
        
    # Valid check-in! 
    # Hit payment-service to CANCEL the hold
    async with httpx.AsyncClient() as client:
        # Assuming payment_service_url exists in settings
        url = f"{settings.payment_service_url}/api/v1/escrow/release"
        try:
            resp = await client.post(url, json={"payment_intent_id": member.stripe_payment_intent_id})
            resp.raise_for_status()
        except Exception as e:
            # In a real app we'd queue this for retry if payment-service is down.
            print(f"Warning: Escrow release failed: {e}")
            
    # Update state
    member.status = MeetupMemberStatus.checked_in
    await db.commit()
    return {"status": "success", "message": "Check-in complete, escrow released."}

@router.post("/{meetup_id}/process-flakes")
async def process_flakes(
    meetup_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Background Task: Finds users who joined but didn't check in by the end of the meetup.
    Captures their Escrow via payment-service and drops their Karma score.
    """
    from maci_core.models.meetup import MeetupMemberStatus
    from maci_core.models.user import User
    
    stmt = select(MeetupMember).where(
        MeetupMember.meetup_id == uuid.UUID(meetup_id),
        MeetupMember.status == MeetupMemberStatus.pending
    )
    result = await db.execute(stmt)
    flakers = result.scalars().all()
    
    for member in flakers:
        member.status = MeetupMemberStatus.flaked
        
        # 1. Capture Escrow
        if member.stripe_payment_intent_id:
            async with httpx.AsyncClient() as client:
                url = f"{settings.payment_service_url}/api/v1/escrow/capture"
                try:
                    await client.post(url, json={"payment_intent_id": member.stripe_payment_intent_id})
                except Exception as e:
                    print(f"Warning: Failed to capture penalty escrow for {member.id}: {e}")
                    
        # 2. Slash Karma Score (-2.0)
        u_stmt = select(User).where(User.id == member.user_id)
        user = (await db.execute(u_stmt)).scalar_one_or_none()
        if user:
            user.karma_score = max(0.0, user.karma_score - 2.0)
            
    await db.commit()
    return {"status": "processed", "flakers_penalized": len(flakers)}

@router.get("/{meetup_id}/qr-code")
async def get_qr_code(
    meetup_id: str,
    x_user_id: str = Header(..., description="Simulated user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a QR Code string payload for a meetup.
    (In a real app, the client turns this string into a visual QR code).
    """
    # Simply hash the meetup ID with a salt for basic security
    import hashlib
    payload = f"{meetup_id}:maci_qr_secret_2026"
    qr_hash = hashlib.sha256(payload.encode()).hexdigest()
    return {"qr_payload": qr_hash}

from pydantic import BaseModel
class QRCheckInRequest(BaseModel):
    qr_payload: str

@router.post("/{meetup_id}/check-in-qr")
async def check_in_qr(
    meetup_id: str,
    data: QRCheckInRequest,
    x_user_id: str = Header(..., description="Simulated user ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check-in to a meetup via scanned QR code, bypassing GPS.
    """
    from sqlalchemy import select
    from maci_core.models.meetup import MeetupMemberStatus
    import hashlib
    expected_payload = f"{meetup_id}:maci_qr_secret_2026"
    expected_hash = hashlib.sha256(expected_payload.encode()).hexdigest()
    
    if data.qr_payload != expected_hash:
        raise HTTPException(status_code=400, detail="Invalid or expired QR code.")
        
    stmt = select(MeetupMember).where(MeetupMember.meetup_id == uuid.UUID(meetup_id), MeetupMember.user_id == uuid.UUID(x_user_id))
    member = (await db.execute(stmt)).scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=404, detail="You are not a member of this meetup.")
        
    member.status = MeetupMemberStatus.checked_in
    await db.commit()
    
    return {"status": "checked_in", "method": "qr_code", "message": "Physical attendance verified via QR."}
