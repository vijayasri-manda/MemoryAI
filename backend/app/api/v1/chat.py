"""
Chat API endpoints: conversations and streaming messages.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services.auth_service import get_current_user
from app.services.chat_service import ChatService
from app.vector_store.factory import get_vector_store

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    vector_store=Depends(get_vector_store),
) -> ChatService:
    return ChatService(db, vector_store)


# ── Conversations ─────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Create a new conversation."""
    return await service.create_conversation(current_user, data)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationListResponse:
    """List user's conversations (paginated, excluding archived)."""
    return await service.list_conversations(current_user, page, page_size)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationDetailResponse:
    """Get a conversation with all its messages."""
    return await service.get_conversation(conversation_id, current_user)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Update conversation title or archive status."""
    return await service.update_conversation(conversation_id, current_user, data)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> None:
    """Permanently delete a conversation and its messages."""
    await service.delete_conversation(conversation_id, current_user)


# ── Messaging ─────────────────────────────────────────────────────────────────

@router.post("/send")
@router.post("/message")
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    Send a message and receive a streaming response via Server-Sent Events.
    
    Each SSE event is a JSON line:
    - `{"type": "metadata", "conversation_id": "...", "memories_used": N}`
    - `{"type": "chunk", "content": "..."}`
    - `{"type": "done", "conversation_id": "..."}`
    - `{"type": "error", "detail": "..."}`
    """
    async def event_stream():
        async for chunk in service.stream_chat(request, current_user):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Summarization ─────────────────────────────────────────────────────────────

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    request: SummarizeRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> SummarizeResponse:
    """Generate and save a summary for a conversation."""
    return await service.summarize_conversation(request.conversation_id, current_user)
