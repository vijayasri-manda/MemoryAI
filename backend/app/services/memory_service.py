"""
Memory service: CRUD operations for Memory records in PostgreSQL.
Works alongside the vector store for full memory lifecycle management.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.logging import get_logger
from app.models.memory import Memory, MemorySummary
from app.schemas.memory import (
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    MemoryStatsResponse,
    MemoryUpdate,
)
from app.vector_store.base import BaseVectorStore, VectorDocument

logger = get_logger(__name__)


class MemoryService:
    def __init__(self, db: AsyncSession, vector_store: BaseVectorStore) -> None:
        self.db = db
        self.vector_store = vector_store

    def _to_response(self, memory: Memory) -> MemoryResponse:
        tags = None
        if memory.tags:
            try:
                tags = json.loads(memory.tags)
            except Exception:
                tags = [memory.tags]

        return MemoryResponse(
            id=memory.id,
            user_id=memory.user_id,
            conversation_id=memory.conversation_id,
            content=memory.content,
            summary=memory.summary,
            memory_type=memory.memory_type,
            tags=tags,
            importance_score=memory.importance_score,
            access_count=memory.access_count,
            last_accessed_at=memory.last_accessed_at,
            is_active=memory.is_active,
            version=getattr(memory, "version", 1),
            status=getattr(memory, "status", "ACTIVE"),
            expires_at=memory.expires_at,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )

    async def list_memories(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "importance",
    ) -> MemoryListResponse:
        conditions = [Memory.user_id == user_id]

        if is_active is not None:
            conditions.append(Memory.is_active == is_active)

        if min_importance > 0.0:
            conditions.append(Memory.importance_score >= min_importance)

        if memory_type:
            conditions.append(Memory.memory_type == memory_type.lower())

        if status:
            conditions.append(Memory.status == status.upper())

        if search_query:
            q_str = f"%{search_query}%"
            conditions.append(
                or_(
                    Memory.content.ilike(q_str),
                    Memory.tags.ilike(q_str),
                    Memory.memory_type.ilike(q_str),
                )
            )

        # Count total
        count_q = select(func.count()).select_from(Memory).where(and_(*conditions))
        total = (await self.db.execute(count_q)).scalar() or 0

        # Sorting
        if sort_by == "created_at":
            order_clause = Memory.created_at.desc()
        elif sort_by == "updated_at":
            order_clause = Memory.updated_at.desc()
        else:
            order_clause = Memory.importance_score.desc()

        # Paginate
        offset = (page - 1) * page_size
        q = (
            select(Memory)
            .where(and_(*conditions))
            .order_by(order_clause, Memory.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        memories = result.scalars().all()

        return MemoryListResponse(
            items=[self._to_response(m) for m in memories],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_memory(self, memory_id: UUID, user_id: UUID) -> MemoryResponse:
        result = await self.db.execute(select(Memory).where(Memory.id == memory_id))
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found.")
        if memory.user_id != user_id:
            raise AuthorizationError()

        # Update access tracking
        memory.access_count += 1
        memory.last_accessed_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        return self._to_response(memory)

    async def update_memory(
        self, memory_id: UUID, user_id: UUID, data: MemoryUpdate
    ) -> MemoryResponse:
        result = await self.db.execute(select(Memory).where(Memory.id == memory_id))
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found.")
        if memory.user_id != user_id:
            raise AuthorizationError()

        update_data = data.model_dump(exclude_none=True)
        if "tags" in update_data:
            update_data["tags"] = json.dumps(update_data["tags"])

        for field, value in update_data.items():
            setattr(memory, field, value)

        memory.version += 1
        memory.status = "UPDATED"
        memory.updated_at = datetime.now(tz=timezone.utc)

        # Re-embed in ChromaDB if content changed
        if data.content:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            new_embedding = await embedding_service.embed_text(data.content)
            await self.vector_store.update_document(
                VectorDocument(
                    id=str(memory_id),
                    content=data.content,
                    embedding=new_embedding,
                    metadata={
                        "user_id": str(user_id),
                        "memory_type": memory.memory_type,
                        "importance_score": memory.importance_score,
                        "version": memory.version,
                        "status": "UPDATED",
                    },
                )
            )

        await self.db.commit()
        await self.db.refresh(memory)
        return self._to_response(memory)

    async def archive_memory(self, memory_id: UUID, user_id: UUID) -> MemoryResponse:
        result = await self.db.execute(select(Memory).where(Memory.id == memory_id))
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found.")
        if memory.user_id != user_id:
            raise AuthorizationError()

        memory.is_active = False
        memory.status = "ARCHIVED"
        memory.updated_at = datetime.now(tz=timezone.utc)

        # Remove vector from vector store so it's excluded from RAG retrieval
        await self.vector_store.delete_documents([str(memory_id)])
        await self.db.commit()
        await self.db.refresh(memory)
        return self._to_response(memory)

    async def restore_memory(self, memory_id: UUID, user_id: UUID) -> MemoryResponse:
        result = await self.db.execute(select(Memory).where(Memory.id == memory_id))
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found.")
        if memory.user_id != user_id:
            raise AuthorizationError()

        memory.is_active = True
        memory.status = "ACTIVE"
        memory.updated_at = datetime.now(tz=timezone.utc)

        # Re-embed vector in vector store
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        embedding = await embedding_service.embed_text(memory.content)
        await self.vector_store.add_documents([
            VectorDocument(
                id=str(memory_id),
                content=memory.content,
                embedding=embedding,
                metadata={
                    "user_id": str(user_id),
                    "memory_type": memory.memory_type,
                    "importance_score": memory.importance_score,
                    "status": "ACTIVE",
                },
            )
        ])

        await self.db.commit()
        await self.db.refresh(memory)
        return self._to_response(memory)

    async def delete_memory(self, memory_id: UUID, user_id: UUID) -> None:
        result = await self.db.execute(select(Memory).where(Memory.id == memory_id))
        memory = result.scalar_one_or_none()
        if not memory:
            raise NotFoundError("Memory not found.")
        if memory.user_id != user_id:
            raise AuthorizationError()

        # Delete from vector store
        await self.vector_store.delete_documents([str(memory_id)])

        # Delete from postgres
        await self.db.delete(memory)
        await self.db.commit()

    async def search_memories(
        self, user_id: UUID, request: MemorySearchRequest
    ) -> MemorySearchResponse:
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_text(request.query)

        filter_meta: dict = {"user_id": str(user_id)}
        if request.memory_type:
            filter_meta["memory_type"] = request.memory_type.lower()

        raw_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            filter_metadata=filter_meta,
            score_threshold=0.0,
        )

        results: list[MemorySearchResult] = []
        for r in raw_results:
            if r.metadata.get("importance_score", 1.0) < request.min_importance:
                continue
            try:
                memory_uuid = UUID(r.id)
                db_result = await self.db.execute(
                    select(Memory).where(Memory.id == memory_uuid, Memory.is_active == True)
                )
                memory = db_result.scalar_one_or_none()
                if memory:
                    results.append(
                        MemorySearchResult(
                            memory=self._to_response(memory),
                            similarity_score=r.similarity_score,
                        )
                    )
            except Exception:
                continue

        return MemorySearchResponse(
            results=results,
            query=request.query,
            total=len(results),
        )

    async def get_stats(self, user_id: UUID) -> MemoryStatsResponse:
        total_q = select(func.count()).select_from(Memory).where(Memory.user_id == user_id)
        active_q = select(func.count()).select_from(Memory).where(
            Memory.user_id == user_id, Memory.is_active == True
        )
        updated_q = select(func.count()).select_from(Memory).where(
            Memory.user_id == user_id, Memory.status == "UPDATED"
        )
        summaries_q = select(func.count()).select_from(MemorySummary).where(
            MemorySummary.user_id == user_id
        )
        avg_q = select(func.avg(Memory.importance_score)).where(Memory.user_id == user_id)
        access_q = select(func.sum(Memory.access_count)).where(Memory.user_id == user_id)
        max_updated_q = select(func.max(Memory.updated_at)).where(Memory.user_id == user_id)

        total = (await self.db.execute(total_q)).scalar() or 0
        active = (await self.db.execute(active_q)).scalar() or 0
        updated = (await self.db.execute(updated_q)).scalar() or 0
        summaries = (await self.db.execute(summaries_q)).scalar() or 0
        avg_importance = float((await self.db.execute(avg_q)).scalar() or 0)
        total_access = (await self.db.execute(access_q)).scalar() or 0
        last_updated = (await self.db.execute(max_updated_q)).scalar()

        # Count by type
        type_q = (
            select(Memory.memory_type, func.count())
            .where(Memory.user_id == user_id)
            .group_by(Memory.memory_type)
        )
        type_rows = (await self.db.execute(type_q)).all()
        by_type = {row[0]: row[1] for row in type_rows}

        return MemoryStatsResponse(
            total_memories=total,
            active_memories=active,
            updated_memories=updated,
            summaries_count=summaries,
            by_type=by_type,
            avg_importance=round(avg_importance, 3),
            total_access_count=total_access,
            last_updated=last_updated,
        )

    async def expire_memories(self) -> int:
        """Deactivate expired memories. Call periodically as background task."""
        now = datetime.now(tz=timezone.utc)
        result = await self.db.execute(
            update(Memory)
            .where(Memory.expires_at <= now, Memory.is_active == True)
            .values(is_active=False, status="ARCHIVED")
            .returning(Memory.id)
        )
        expired_ids = [str(row[0]) for row in result.all()]

        if expired_ids:
            await self.vector_store.delete_documents(expired_ids)
            logger.info("Expired memories deactivated", count=len(expired_ids))

        await self.db.commit()
        return len(expired_ids)
