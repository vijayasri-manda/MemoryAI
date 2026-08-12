"""
Memory management API endpoints for Memory Dashboard & Administration.
"""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.memory import (
    MemoryListResponse,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatsResponse,
    MemoryUpdate,
)
from app.services.auth_service import get_current_user
from app.services.memory_service import MemoryService
from app.vector_store.factory import get_vector_store

router = APIRouter(prefix="/memories", tags=["Memory"])


def get_memory_service(
    db: AsyncSession = Depends(get_db),
    vector_store=Depends(get_vector_store),
) -> MemoryService:
    return MemoryService(db, vector_store)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    memory_type: Optional[str] = Query(None),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    is_active: Optional[bool] = Query(None),
    search_query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("importance"),
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryListResponse:
    """List memories for the authenticated user (paginated, sorted, filtered)."""
    return await service.list_memories(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        memory_type=memory_type,
        min_importance=min_importance,
        is_active=is_active,
        search_query=search_query,
        status=status,
        sort_by=sort_by,
    )


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryStatsResponse:
    """Get memory statistics for the Dashboard."""
    return await service.get_stats(current_user.id)


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(
    request: MemorySearchRequest,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemorySearchResponse:
    """Semantic search over user's memories using vector similarity."""
    return await service.search_memories(current_user.id, request)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Get detailed information for a specific memory."""
    return await service.get_memory(memory_id, current_user.id)


@router.put("/{memory_id}", response_model=MemoryResponse)
@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    data: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Edit content, category, tags, or importance score of a memory."""
    return await service.update_memory(memory_id, current_user.id, data)


@router.post("/{memory_id}/archive", response_model=MemoryResponse)
async def archive_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Archive a memory (excludes from active RAG retrieval)."""
    return await service.archive_memory(memory_id, current_user.id)


@router.post("/{memory_id}/restore", response_model=MemoryResponse)
async def restore_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Restore an archived memory back to active state."""
    return await service.restore_memory(memory_id, current_user.id)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MemoryService = Depends(get_memory_service),
) -> None:
    """Delete a memory permanently from PostgreSQL and ChromaDB."""
    await service.delete_memory(memory_id, current_user.id)
