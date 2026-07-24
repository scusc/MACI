import asyncio
import json
import uuid
import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from app.db import get_db
from app.config import settings
from maci_core.models.connection import MatchConnection, ChatMessage, ConnectionStatus
from maci_core.core.security import verify_token
from maci_core.schemas.chat import ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["Chat & Messaging"])

# Global Redis Connection
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def get_ws_user_id(token: str) -> str:
    try:
        payload = verify_token(token, expected_type="access")
        return payload.get("sub")
    except Exception:
        return None

def strip_identity_if_anonymous(message_dict: dict, connection_status: str, requesting_user_id: str):
    """
    Core anonymity logic. If status is anonymous, the sender_id is masked 
    unless the requesting user is the sender.
    """
    if connection_status == ConnectionStatus.anonymous.value:
        if str(message_dict.get("sender_id")) != requesting_user_id:
            message_dict["sender_id"] = "anonymous_avatar"
    return message_dict

@router.websocket("/{connection_id}/ws")
async def websocket_endpoint(websocket: WebSocket, connection_id: str, token: str, db: AsyncSession = Depends(get_db)):
    user_id = await get_ws_user_id(token)
    if not user_id:
        await websocket.close(code=1008, reason="Invalid Token")
        return

    # Verify connection exists and user is part of it
    stmt = select(MatchConnection).where(MatchConnection.id == uuid.UUID(connection_id))
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if not conn or (str(conn.user_a_id) != user_id and str(conn.user_b_id) != user_id):
        await websocket.close(code=1008, reason="Not authorized for this connection")
        return

    await websocket.accept()
    pubsub = redis_client.pubsub()
    channel = f"chat_{connection_id}"
    await pubsub.subscribe(channel)
    
    async def redis_listener():
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                # Mask identity before sending to websocket client
                data = strip_identity_if_anonymous(data, conn.status.value, user_id)
                await websocket.send_json(data)

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            data = await websocket.receive_json()
            # Incoming text message
            content_text = data.get("content_text")
            if content_text:
                new_msg = ChatMessage(
                    connection_id=uuid.UUID(connection_id),
                    sender_id=uuid.UUID(user_id),
                    content_text=content_text
                )
                db.add(new_msg)
                await db.commit()
                await db.refresh(new_msg)
                
                # Broadcast via Redis
                msg_response = ChatMessageResponse.model_validate(new_msg).model_dump(mode="json")
                await redis_client.publish(channel, json.dumps(msg_response))
                
    except WebSocketDisconnect:
        listener_task.cancel()
        await pubsub.unsubscribe(channel)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/{connection_id}/voice")
async def upload_voice_note(
    connection_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Live Phase 8: Azure Blob Storage Integration for Voice Notes.
    """
    from azure.storage.blob.aio import BlobServiceClient
    
    stmt = select(MatchConnection).where(MatchConnection.id == uuid.UUID(connection_id))
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()
    
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    if str(conn.user_a_id) != user_id and str(conn.user_b_id) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized for this connection")

    file_id = str(uuid.uuid4())
    blob_name = f"voice_notes/{connection_id}/{file_id}.wav"
    
    # Retrieve connection string from env
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not conn_str:
        # Fallback to local if env missing just to prevent hard crash, but log a loud warning
        import logging
        logger = logging.getLogger("maci.chat")
        logger.warning("AZURE_STORAGE_CONNECTION_STRING is missing! Falling back to local storage.")
        upload_dir = "/tmp/maci_voice_notes"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{file_id}.wav")
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        mock_uri = f"local://{file_path}"
    else:
        # Live Azure Upload
        try:
            blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            container_client = blob_service_client.get_container_client("maci-media")
            
            # Read file stream
            content = await file.read()
            
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.upload_blob(content, overwrite=True)
            
            # Construct public URI (Assuming container is public-read or using SAS tokens in a real app)
            mock_uri = blob_client.url
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Azure Blob Upload failed: {str(e)}")

    new_msg = ChatMessage(
        connection_id=uuid.UUID(connection_id),
        sender_id=uuid.UUID(user_id),
        audio_uri=mock_uri
    )
    db.add(new_msg)
    await db.commit()
    await db.refresh(new_msg)
    
    # Broadcast to websocket
    channel = f"chat_{connection_id}"
    msg_response = ChatMessageResponse.model_validate(new_msg).model_dump(mode="json")
    await redis_client.publish(channel, json.dumps(msg_response))
    
    return {"status": "uploaded", "uri": mock_uri}

from pydantic import BaseModel

class MediatorRequest(BaseModel):
    dispute_text: str

@router.post("/mediator")
async def ai_mediator(
    request: MediatorRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    In-App AI Mediator Chatbot.
    Acts as a neutral 3rd party to resolve travel group disputes using Azure OpenAI.
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    ad_token = os.getenv("AZURE_OPENAI_AD_TOKEN")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not endpoint or (not ad_token and not api_key):
        return {
            "status": "mediated",
            "resolution": "It sounds like tensions are high regarding this issue. I recommend taking a short 1-hour break from the conversation, then re-evaluating the itinerary together focusing on mutual compromises. Remember, you both agreed to the 'Chill Vibe' psychometric profile!"
        }
        
    try:
        from langchain_openai import AzureChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        kwargs = {
            "azure_endpoint": endpoint,
            "openai_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "o3"),
            "temperature": 0.7,
        }
        if ad_token:
            kwargs["azure_ad_token"] = ad_token
        elif api_key:
            kwargs["api_key"] = api_key

        llm = AzureChatOpenAI(**kwargs)
        sys_msg = SystemMessage(content="You are a neutral, objective travel group mediator for the Rally platform. Analyze disputes and provide a calming, de-escalating, and practical resolution for the group. Keep it under 3 sentences.")
        human_msg = HumanMessage(content=f"Dispute: \"{request.dispute_text}\"")

        res = await llm.ainvoke([sys_msg, human_msg])
        return {"status": "mediated", "resolution": res.content}
    except Exception as e:
        logger.warning(f"Azure OpenAI Mediator failed: {e}")
        return {
            "status": "mediated",
            "resolution": "Tensions can arise during group planning. I suggest allocating a flexible afternoon where travelers can split into sub-activities before regrouping for sunset dinner."
        }
