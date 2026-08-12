"""
Summary Service: Dedicated service responsible for generating, updating,
embedding, and retrieving conversation summaries for hierarchical RAG retrieval.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.memory import MemorySummary
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service, ChatMessage
from app.vector_store.base import BaseVectorStore, VectorDocument

logger = get_logger(__name__)


class SummaryService:
    """
    Service responsible for:
    - Generating structured conversation summaries using LLM
    - Updating existing conversation summaries (preventing duplicates)
    - Embedding summaries and storing in ChromaDB under 'summary' namespace
    - Retrieving relevant conversation summaries during RAG query processing
    """

    def __init__(self, db: AsyncSession, vector_store: BaseVectorStore) -> None:
        self.db = db
        self.vector_store = vector_store

    async def generate_summary_text(self, conversation_history: list[dict]) -> tuple[str, list[str]]:
        """
        Calls LLM to generate a structured summary of conversation history.
        Returns (summary_text, topics_list).
        """
        if not conversation_history:
            return "No conversation messages to summarize.", []

        formatted_history = "\n".join(
            f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}"
            for m in conversation_history
        )

        prompt = (
            "Analyze the following conversation and generate a concise, structured summary containing:\n"
            "- Main Topics Discussed\n"
            "- Projects & Tech Stack\n"
            "- User Preferences & Goals\n"
            "- Coding Decisions & Learning Progress\n"
            "- Key Conclusions & Next Tasks\n\n"
            f"Conversation:\n{formatted_history}\n\n"
            "Summary Format:\n"
            "Project: <details>\n"
            "Tech Stack: <details>\n"
            "Topics: <topic1, topic2, topic3>\n"
            "Progress & Conclusions: <details>\n"
        )

        llm = get_llm_service()
        try:
            summary_response = await llm.complete([ChatMessage(role="user", content=prompt)])
            summary_text = summary_response.strip()
        except Exception as e:
            logger.warning("LLM summary generation failed, falling back to rule-based", error=str(e))
            summary_text = f"Summary of {len(conversation_history)} messages in conversation."

        # Extract topics
        topics = []
        for line in summary_text.splitlines():
            if "Topics:" in line:
                topics_part = line.split("Topics:", 1)[1]
                topics = [t.strip() for t in topics_part.split(",") if t.strip()]

        if not topics:
            topics = ["Conversation", "AI Memory"]

        return summary_text, topics

    async def upsert_summary(
        self,
        conversation_id: UUID | str,
        user_id: UUID | str,
        conversation_history: list[dict],
    ) -> MemorySummary:
        """
        Generates/updates a conversation summary in PostgreSQL and ChromaDB.
        Updates existing summary record if one exists.
        """
        conv_uuid = UUID(str(conversation_id))
        user_uuid = UUID(str(user_id))

        summary_text, topics = await self.generate_summary_text(conversation_history)
        token_count = len(summary_text.split())
        topics_json = json.dumps(topics)

        # Check existing summary in DB
        result = await self.db.execute(
            select(MemorySummary).where(
                MemorySummary.conversation_id == conv_uuid,
                MemorySummary.user_id == user_uuid,
            )
        )
        existing_summary = result.scalar_one_or_none()

        embedding_service = get_embedding_service()
        summary_embedding = await embedding_service.embed_text(summary_text)

        if existing_summary:
            existing_summary.summary = summary_text
            existing_summary.topics = topics_json
            existing_summary.token_count = token_count
            existing_summary.message_range_end = len(conversation_history)
            existing_summary.updated_at = datetime.now(tz=timezone.utc)
            db_record = existing_summary
            vector_id = existing_summary.vector_store_id or f"summary_{existing_summary.id}"
        else:
            summary_id = uuid.uuid4()
            vector_id = f"summary_{summary_id}"
            db_record = MemorySummary(
                id=summary_id,
                user_id=user_uuid,
                conversation_id=conv_uuid,
                summary=summary_text,
                topics=topics_json,
                message_range_start=0,
                message_range_end=len(conversation_history),
                token_count=token_count,
                vector_store_id=vector_id,
            )
            self.db.add(db_record)

        # Store/Update in ChromaDB with is_summary metadata flag
        vector_doc = VectorDocument(
            id=vector_id,
            content=summary_text,
            embedding=summary_embedding,
            metadata={
                "user_id": str(user_id),
                "conversation_id": str(conversation_id),
                "is_summary": True,
                "type": "summary",
                "topics": topics_json,
            },
        )

        if existing_summary:
            await self.vector_store.update_document(vector_doc)
        else:
            await self.vector_store.add_documents([vector_doc])

        await self.db.commit()
        await self.db.refresh(db_record)

        logger.info(
            "Conversation summary upserted",
            conversation_id=str(conversation_id),
            token_count=token_count,
        )
        return db_record

    async def retrieve_relevant_summaries(
        self,
        query: str,
        user_id: str,
        top_k: int = 3,
    ) -> list[str]:
        """
        Retrieves top-k relevant conversation summaries from ChromaDB.
        """
        try:
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.embed_text(query)

            raw_results = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_metadata={"user_id": user_id, "is_summary": True},
                score_threshold=0.55,
            )

            summaries = [res.content for res in raw_results if res.content]
            logger.info("Retrieved relevant summaries", query=query[:40], count=len(summaries))
            return summaries
        except Exception as e:
            logger.warning("Failed to retrieve conversation summaries", error=str(e))
            return []
