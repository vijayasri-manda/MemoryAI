"""
Memory Lifecycle Service: Responsible for intelligent memory management,
duplicate detection, similarity checking, update decisions, versioning,
and transactional sync between PostgreSQL and ChromaDB.
"""

from __future__ import annotations

import difflib
import json
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.memory import Memory
from app.services.embedding_service import get_embedding_service
from app.services.memory_extraction_service import MemoryObject
from app.vector_store.base import BaseVectorStore, VectorDocument

logger = get_logger(__name__)

LifecycleDecision = Literal["CREATE", "UPDATE", "REPLACE", "IGNORE"]


class MemoryLifecycleResult:
    def __init__(
        self,
        decision: LifecycleDecision,
        memory_id: str,
        reason: str,
        updated_memory: Optional[Memory] = None,
    ) -> None:
        self.decision = decision
        self.memory_id = memory_id
        self.reason = reason
        self.updated_memory = updated_memory


class MemoryLifecycleService:
    """
    Service managing the full memory lifecycle:
    - Duplicate detection
    - Similarity checking
    - Update decisions (CREATE / UPDATE / REPLACE / IGNORE)
    - Versioning and status management (ACTIVE, UPDATED, ARCHIVED, DELETED)
    - Transactional updates across PostgreSQL and ChromaDB
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_store: BaseVectorStore,
        similarity_threshold: float = 0.85,
    ) -> None:
        self.db = db
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Return ratio between 0.0 and 1.0 indicating string similarity."""
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def evaluate_update_rule(
        self,
        new_memory: MemoryObject,
        existing_content: str,
        existing_category: str,
        sim_score: float,
    ) -> LifecycleDecision:
        """
        Apply category-specific lifecycle rules to decide action:
        - Preference: Always keep latest value.
        - Goal: Keep latest goal if conflicting.
        - Project: Multiple active projects allowed unless identical.
        - Learning: Update if subject changes.
        - Temporary: Automatically replace.
        - Coding: Update when architectural decisions change.
        - Personal: Update when newer info conflicts.
        """
        text_sim = self.calculate_text_similarity(new_memory.content, existing_content)

        # 1. Exact or near-exact match -> IGNORE
        if text_sim > 0.92 or (sim_score > 0.95 and text_sim > 0.85):
            return "IGNORE"

        category = new_memory.category

        # 2. Temporary memories -> REPLACE
        if category == "Temporary":
            return "REPLACE"

        # 3. Preference -> UPDATE if same preference domain
        if category in ("Preference", "preferences"):
            return "UPDATE"

        # 4. Goal -> UPDATE if changing goal
        if category in ("Goal", "goals"):
            return "UPDATE"

        # 5. Learning -> UPDATE if subject changes
        if category in ("Learning", "learning_progress"):
            return "UPDATE"

        # 6. Coding -> UPDATE if architectural decision changes
        if category in ("Coding", "coding_decisions", "decision"):
            return "UPDATE"

        # 7. Personal -> UPDATE if conflicting personal info
        if category in ("Personal", "important_facts"):
            return "UPDATE"

        # 8. Project -> UPDATE if same project name, CREATE if distinct project
        if category in ("Project", "projects"):
            if text_sim > 0.5:
                return "UPDATE"
            return "CREATE"

        if sim_score >= self.similarity_threshold:
            return "UPDATE"

        return "CREATE"

    async def process_extracted_memory(
        self,
        extracted: MemoryObject,
        user_id: UUID | str,
        conversation_id: UUID | str | None = None,
        source_message_id: UUID | str | None = None,
    ) -> MemoryLifecycleResult:
        """
        Processes an extracted memory object through duplicate detection & lifecycle rules.
        Executes database & vector store operations transactionally.
        """
        user_str = str(user_id)
        if not extracted.is_worth_storing or extracted.importance <= 0.0:
            return MemoryLifecycleResult(
                decision="IGNORE",
                memory_id="",
                reason="Memory marked as low importance or noise",
            )

        embedding_service = get_embedding_service()
        memory_embedding = await embedding_service.embed_text(extracted.content)

        # Step 1: Search existing memories for current user
        similar_vector_results = await self.vector_store.similarity_search(
            query_embedding=memory_embedding,
            top_k=5,
            filter_metadata={"user_id": user_str},
            score_threshold=0.65,
        )

        target_memory: Memory | None = None
        highest_sim_score = 0.0

        for res in similar_vector_results:
            try:
                mem_uuid = UUID(res.id)
                db_result = await self.db.execute(
                    select(Memory).where(
                        Memory.id == mem_uuid,
                        Memory.user_id == UUID(user_str),
                        Memory.is_active == True,
                    )
                )
                db_mem = db_result.scalar_one_or_none()
                if db_mem:
                    target_memory = db_mem
                    highest_sim_score = res.similarity_score
                    break
            except Exception:
                continue

        # Step 2: If no similar memory exists -> CREATE
        if not target_memory or highest_sim_score < 0.70:
            return await self._create_memory(
                extracted, memory_embedding, user_str, conversation_id, source_message_id
            )

        # Step 3: Evaluate decision rules
        decision = self.evaluate_update_rule(
            new_memory=extracted,
            existing_content=target_memory.content,
            existing_category=target_memory.memory_type,
            sim_score=highest_sim_score,
        )

        if decision == "IGNORE":
            logger.info("Memory lifecycle: IGNORE (already exists)", content=extracted.content[:40])
            return MemoryLifecycleResult(
                decision="IGNORE",
                memory_id=str(target_memory.id),
                reason="Duplicate memory already stored",
                updated_memory=target_memory,
            )

        elif decision == "UPDATE":
            return await self._update_memory(
                target_memory, extracted, memory_embedding, user_str
            )

        elif decision == "REPLACE":
            # Archive old memory, create new
            await self._archive_memory(target_memory)
            return await self._create_memory(
                extracted, memory_embedding, user_str, conversation_id, source_message_id
            )

        else:  # CREATE
            return await self._create_memory(
                extracted, memory_embedding, user_str, conversation_id, source_message_id
            )

    async def _create_memory(
        self,
        extracted: MemoryObject,
        embedding: list[float],
        user_id: str,
        conversation_id: UUID | str | None,
        source_message_id: UUID | str | None,
    ) -> MemoryLifecycleResult:
        memory_id = str(uuid.uuid4())

        expires_at = None
        if settings.MEMORY_TTL_DAYS > 0:
            from datetime import timedelta
            expires_at = datetime.now(tz=timezone.utc) + timedelta(days=settings.MEMORY_TTL_DAYS)

        tags_json = json.dumps(extracted.tags)
        conv_uuid = UUID(str(conversation_id)) if conversation_id else None
        src_msg_uuid = UUID(str(source_message_id)) if source_message_id else None

        # 1. PostgreSQL insert
        new_mem = Memory(
            id=UUID(memory_id),
            user_id=UUID(user_id),
            conversation_id=conv_uuid,
            content=extracted.content,
            memory_type=extracted.category.lower(),
            importance_score=extracted.importance,
            tags=tags_json,
            is_active=True,
            version=1,
            status="ACTIVE",
            expires_at=expires_at,
            source_message_id=src_msg_uuid,
            embedding_model=settings.EMBEDDING_MODEL,
            vector_store_id=memory_id,
        )
        self.db.add(new_mem)

        # 2. ChromaDB insert
        vector_doc = VectorDocument(
            id=memory_id,
            content=extracted.content,
            embedding=embedding,
            metadata={
                "user_id": user_id,
                "conversation_id": str(conversation_id) if conversation_id else "",
                "memory_type": extracted.category.lower(),
                "importance_score": extracted.importance,
                "confidence": extracted.confidence,
                "tags": tags_json,
                "version": 1,
                "status": "ACTIVE",
            },
        )
        await self.vector_store.add_documents([vector_doc])
        await self.db.commit()

        logger.info("Memory lifecycle: CREATE new memory", memory_id=memory_id, category=extracted.category)
        return MemoryLifecycleResult(
            decision="CREATE",
            memory_id=memory_id,
            reason="Created new memory record",
            updated_memory=new_mem,
        )

    async def _update_memory(
        self,
        existing_mem: Memory,
        extracted: MemoryObject,
        embedding: list[float],
        user_id: str,
    ) -> MemoryLifecycleResult:
        existing_mem.content = extracted.content
        existing_mem.memory_type = extracted.category.lower()
        existing_mem.importance_score = extracted.importance
        existing_mem.tags = json.dumps(extracted.tags)
        existing_mem.version += 1
        existing_mem.status = "UPDATED"
        existing_mem.updated_at = datetime.now(tz=timezone.utc)

        # Update ChromaDB vector
        vector_doc = VectorDocument(
            id=str(existing_mem.id),
            content=extracted.content,
            embedding=embedding,
            metadata={
                "user_id": user_id,
                "memory_type": extracted.category.lower(),
                "importance_score": extracted.importance,
                "confidence": extracted.confidence,
                "tags": json.dumps(extracted.tags),
                "version": existing_mem.version,
                "status": "UPDATED",
            },
        )
        await self.vector_store.update_document(vector_doc)
        await self.db.commit()

        logger.info("Memory lifecycle: UPDATE memory", memory_id=str(existing_mem.id), version=existing_mem.version)
        return MemoryLifecycleResult(
            decision="UPDATE",
            memory_id=str(existing_mem.id),
            reason=f"Updated memory to version {existing_mem.version}",
            updated_memory=existing_mem,
        )

    async def _archive_memory(self, existing_mem: Memory) -> None:
        existing_mem.is_active = False
        existing_mem.status = "ARCHIVED"
        existing_mem.updated_at = datetime.now(tz=timezone.utc)
        await self.vector_store.delete_documents([str(existing_mem.id)])
        logger.info("Memory lifecycle: ARCHIVED memory", memory_id=str(existing_mem.id))
