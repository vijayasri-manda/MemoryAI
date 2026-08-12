"""
Pydantic schemas for Memory management APIs.
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: Optional[UUID] = None
    content: str
    summary: Optional[str] = None
    memory_type: str
    tags: Optional[list[str]] = None
    importance_score: float
    access_count: int
    last_accessed_at: Optional[datetime] = None
    is_active: bool
    version: int = 1
    status: str = "ACTIVE"
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = None
    memory_type: Optional[Literal[
        "general", "preference", "project", "goal", "decision", "skill"
    ]] = None
    tags: Optional[list[str]] = None
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(10, ge=1, le=50)
    memory_type: Optional[str] = None
    min_importance: float = Field(0.0, ge=0.0, le=1.0)


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    similarity_score: float


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]
    query: str
    total: int


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    page: int
    page_size: int


class MemoryStatsResponse(BaseModel):
    total_memories: int
    active_memories: int
    updated_memories: int = 0
    summaries_count: int = 0
    by_type: dict[str, int]
    avg_importance: float
    total_access_count: int
    last_updated: Optional[datetime] = None


class ExportRequest(BaseModel):
    conversation_id: Optional[UUID] = None   # None = export all
    include_memories: bool = True
    format: Literal["json", "markdown"] = "json"


class ImportRequest(BaseModel):
    data: dict   # flexible JSON import format
