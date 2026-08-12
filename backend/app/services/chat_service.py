"""
Chat service: manages conversations, sends messages through the RAG pipeline,
and triggers memory extraction after each exchange.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.models.conversation import Conversation, Message
from app.models.memory import Memory
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.schemas.chat import (
    ChatRequest,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SummarizeResponse,
)
from app.services.llm_service import get_llm_service
from app.vector_store.base import BaseVectorStore

logger = get_logger(__name__)


class ChatService:
    def __init__(self, db: AsyncSession, vector_store: BaseVectorStore) -> None:
        self.db = db
        self.vector_store = vector_store
        self.rag = RAGPipeline(vector_store)

    # ── Conversation CRUD ─────────────────────────────────────────────────────

    async def create_conversation(
        self, user: User, data: ConversationCreate
    ) -> ConversationResponse:
        convo = Conversation(user_id=user.id, title=data.title)
        self.db.add(convo)
        await self.db.commit()
        await self.db.refresh(convo)
        return ConversationResponse.model_validate(convo)

    async def list_conversations(
        self, user: User, page: int = 1, page_size: int = 20
    ) -> ConversationListResponse:
        from sqlalchemy import func

        total_q = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user.id, Conversation.is_archived == False
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        offset = (page - 1) * page_size
        q = (
            select(Conversation)
            .where(Conversation.user_id == user.id, Conversation.is_archived == False)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        conversations = result.scalars().all()

        return ConversationListResponse(
            items=[ConversationResponse.model_validate(c) for c in conversations],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_conversation(
        self, conversation_id: UUID, user: User
    ) -> ConversationDetailResponse:
        q = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        result = await self.db.execute(q)
        convo = result.scalar_one_or_none()

        if not convo:
            raise NotFoundError("Conversation not found.")
        if convo.user_id != user.id:
            raise AuthorizationError()

        return ConversationDetailResponse(
            **ConversationResponse.model_validate(convo).model_dump(),
            messages=[MessageResponse.model_validate(m) for m in convo.messages],
        )

    async def update_conversation(
        self, conversation_id: UUID, user: User, data: ConversationUpdate
    ) -> ConversationResponse:
        convo = await self._get_convo_or_raise(conversation_id, user.id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(convo, field, value)
        await self.db.commit()
        await self.db.refresh(convo)
        return ConversationResponse.model_validate(convo)

    async def delete_conversation(self, conversation_id: UUID, user: User) -> None:
        convo = await self._get_convo_or_raise(conversation_id, user.id)
        # Vector store memories for this conversation will cascade-delete
        # via postgres relationship (Memory.conversation_id SET NULL)
        await self.db.delete(convo)
        await self.db.commit()

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def stream_chat(
        self, request: ChatRequest, user: User
    ) -> AsyncGenerator[str, None]:
        """
        Core chat loop with RAG-injected memory.
        Yields SSE-compatible JSON strings for streaming.
        """
        llm = get_llm_service()

        # Get or create conversation
        if request.conversation_id:
            convo = await self._get_convo_or_raise(request.conversation_id, user.id)
        else:
            convo = Conversation(user_id=user.id, title="New Conversation")
            self.db.add(convo)
            await self.db.flush()

        # Save user message
        user_msg = Message(
            conversation_id=convo.id,
            user_id=user.id,
            role="user",
            content=request.message,
            token_count=len(request.message.split()),
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Load recent conversation history for context
        history = await self._load_history(convo.id, limit=20)

        # Build RAG-augmented prompt with telemetry
        messages, memories_count, debug_info = await self.rag.build_prompt_with_debug(
            user_query=request.message,
            conversation_history=history,
            user_id=str(user.id),
            conversation_id=str(convo.id),
        )

        # Yield metadata event first
        yield json.dumps({
            "type": "metadata",
            "conversation_id": str(convo.id),
            "message_id": str(user_msg.id),
            "memories_used": memories_count,
        }) + "\n"

        # Stream LLM response
        full_response = ""
        t_llm_start = time.perf_counter()
        try:
            async for chunk in llm.stream(messages):
                full_response += chunk
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
        except Exception as e:
            logger.error("LLM streaming error", error=str(e))
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"
            return

        t_llm_ms = (time.perf_counter() - t_llm_start) * 1000

        # Complete debug trace metadata
        from app.core.config import settings
        from app.services.debug_service import DebugService

        debug_info["gemini_response"] = full_response
        debug_info["response_time_ms"] = round(t_llm_ms, 2)
        debug_info["model_name"] = settings.LLM_MODEL
        debug_info["token_usage"] = {
            "prompt_tokens": debug_info.get("prompt_token_length", 0),
            "completion_tokens": len(full_response.split()),
            "total_tokens": debug_info.get("prompt_token_length", 0) + len(full_response.split()),
        }

        DebugService.record_trace(user_id=str(user.id), trace=debug_info)

        # Save assistant message
        assistant_msg = Message(
            conversation_id=convo.id,
            user_id=user.id,
            role="assistant",
            content=full_response,
            token_count=len(full_response.split()),
        )
        self.db.add(assistant_msg)

        # Update conversation stats
        convo.message_count += 2
        convo.token_count += user_msg.token_count + assistant_msg.token_count

        # Auto-update conversation title after first exchange
        if convo.message_count <= 2 and convo.title == "New Conversation":
            convo.title = request.message[:60] + ("..." if len(request.message) > 60 else "")

        await self.db.commit()

        # Trigger async memory extraction (fire-and-forget style)
        await self._extract_and_store_memories(
            messages=[
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": full_response},
            ],
            user_id=str(user.id),
            conversation_id=str(convo.id),
        )

        yield json.dumps({"type": "done", "conversation_id": str(convo.id)}) + "\n"

        # Trigger periodic summarization
        from app.core.config import settings
        if convo.message_count > 0 and convo.message_count % settings.MEMORY_SUMMARY_INTERVAL == 0:
            await self._auto_summarize(convo, user)

    async def summarize_conversation(
        self, conversation_id: UUID, user: User
    ) -> SummarizeResponse:
        convo = await self._get_convo_or_raise(conversation_id, user.id)
        history = await self._load_history(convo.id, limit=100)

        from app.services.summary_service import SummaryService
        summary_service = SummaryService(db=self.db, vector_store=self.vector_store)
        summary_record = await summary_service.upsert_summary(
            conversation_id=convo.id,
            user_id=user.id,
            conversation_history=history,
        )

        convo.summary = summary_record.summary
        await self.db.commit()
        return SummarizeResponse(conversation_id=conversation_id, summary=summary_record.summary)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_convo_or_raise(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise NotFoundError("Conversation not found.")
        if convo.user_id != user_id:
            raise AuthorizationError()
        return convo

    async def _load_history(self, conversation_id: UUID, limit: int = 20) -> list[dict]:
        q = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(q)
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]

    async def _extract_and_store_memories(
        self, messages: list[dict], user_id: str, conversation_id: str
    ) -> None:
        """
        Extract memories after an exchange and pass through MemoryLifecycleService
        for duplicate detection, updates, versioning, and ChromaDB/PostgreSQL sync.
        """
        try:
            from app.services.memory_extraction_service import MemoryExtractionService
            from app.services.memory_lifecycle_service import MemoryLifecycleService

            extraction_service = MemoryExtractionService()
            lifecycle_service = MemoryLifecycleService(
                db=self.db, vector_store=self.vector_store
            )

            # Analyze recent user messages for extraction
            user_texts = [m["content"] for m in messages if m.get("role") == "user"]
            for text in user_texts:
                extracted = extraction_service.process(text)
                if extracted.is_worth_storing and extracted.importance > 0.0:
                    result = await lifecycle_service.process_extracted_memory(
                        extracted=extracted,
                        user_id=user_id,
                        conversation_id=conversation_id,
                    )
                    logger.info(
                        "Memory lifecycle processed",
                        decision=result.decision,
                        memory_id=result.memory_id,
                        reason=result.reason,
                    )
        except Exception as e:
            logger.error("Memory lifecycle extraction failed", error=str(e))

    async def _auto_summarize(self, convo: Conversation, user: User) -> None:
        try:
            await self.summarize_conversation(convo.id, user)
        except Exception as e:
            logger.warning("Auto-summarization failed", error=str(e))
