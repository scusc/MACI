from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ChatMessageBase(BaseModel):
    content_text: Optional[str] = None
    audio_uri: Optional[str] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: UUID
    sender_id: UUID
    connection_id: UUID
    is_system_message: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MatchConnectionResponse(BaseModel):
    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    status: str
    user_a_reveal_vote: bool
    user_b_reveal_vote: bool
    created_at: datetime

    class Config:
        from_attributes = True
