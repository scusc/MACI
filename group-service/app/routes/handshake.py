import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from maci_core.models.connection import MatchConnection, ConnectionStatus
from maci_core.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from maci_core.schemas.chat import MatchConnectionResponse

router = APIRouter(prefix="/handshake", tags=["Trust Handshake"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/request", response_model=MatchConnectionResponse)
async def create_match_connection(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new MatchConnection between two users in 'anonymous' state.
    """
    u_a, u_b = sorted([uuid.UUID(user_id), uuid.UUID(target_user_id)])
    
    # Check if exists
    stmt = select(MatchConnection).where(
        MatchConnection.user_a_id == u_a,
        MatchConnection.user_b_id == u_b
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing
        
    new_conn = MatchConnection(user_a_id=u_a, user_b_id=u_b)
    db.add(new_conn)
    await db.commit()
    await db.refresh(new_conn)
    return new_conn

@router.post("/{connection_id}/vote", response_model=MatchConnectionResponse)
async def vote_to_reveal_identity(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Stage 3: Mutual Identity Reveal Smart Contract.
    If User A votes, it records it. If User B has already voted, 
    the status immediately upgrades to 'identity_revealed'.
    """
    stmt = select(MatchConnection).where(MatchConnection.id == uuid.UUID(connection_id))
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    uid = uuid.UUID(user_id)
    if conn.user_a_id != uid and conn.user_b_id != uid:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if conn.user_a_id == uid:
        conn.user_a_reveal_vote = True
    else:
        conn.user_b_reveal_vote = True
        
    # Smart Contract Logic
    if conn.user_a_reveal_vote and conn.user_b_reveal_vote:
        conn.status = ConnectionStatus.identity_revealed
        
        # Publish a system message to the chat
        new_msg = ChatMessage(
            connection_id=uuid.UUID(connection_id),
            sender_id=uid, # Doesn't matter for system message
            content_text="Identities Revealed!",
            is_system_message=True
        )
        db.add(new_msg)
        await db.flush() # flush to get new_msg.id generated before redis publish
        
        from app.routes.chat import redis_client
        import json
        from maci_core.schemas.chat import ChatMessageResponse
        
        channel = f"chat_{connection_id}"
        msg_response = ChatMessageResponse.model_validate(new_msg).model_dump(mode="json")
        await redis_client.publish(channel, json.dumps(msg_response))
    
    await db.commit()
    await db.refresh(conn)
    
    return conn
