"""
Pydantic schemas for Chat (Conversations and Messages).
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Conversation Schemas ──────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = Field("New Conversation", max_length=255)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    is_archived: Optional[bool] = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    summary: Optional[str] = None
    is_archived: bool
    message_count: int
    token_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    page_size: int


# ── Message Schemas ───────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    token_count: int
    memory_extracted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


# ── Chat Request / Response ───────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request to send a message and get a streamed response."""
    conversation_id: Optional[UUID] = None   # None = create new conversation
    message: str = Field(..., min_length=1, max_length=32_000)
    stream: bool = True


class ChatMetadata(BaseModel):
    """Metadata returned alongside a chat response."""
    conversation_id: UUID
    message_id: UUID
    memories_used: int
    token_count: int


class RegenerateRequest(BaseModel):
    message_id: UUID     # regenerate the assistant response after this message


class SummarizeRequest(BaseModel):
    conversation_id: UUID


class SummarizeResponse(BaseModel):
    conversation_id: UUID
    summary: str
