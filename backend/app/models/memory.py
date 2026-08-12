"""
Memory ORM model — stores metadata about embedded memory chunks.
The actual embeddings live in the vector database; this table stores metadata.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.conversation import Conversation


class Memory(UUIDMixin, TimestampMixin, Base):
    """
    Metadata record for a stored memory chunk.
    The vector embedding is stored in the configured vector store,
    keyed by this record's id (UUID as string).
    """

    __tablename__ = "memories"

    # Ownership
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Classification
    memory_type: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False, index=True
    )  # general | preference | project | goal | decision | skill
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array as text

    # Scoring
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False, index=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lifecycle & Versioning
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False, index=True)  # ACTIVE | UPDATED | ARCHIVED | DELETED
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Source tracking
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vector_store_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memories")
    conversation: Mapped["Conversation | None"] = relationship(
        "Conversation", back_populates="memories"
    )

    def __repr__(self) -> str:
        return f"<Memory id={self.id} type={self.memory_type} importance={self.importance_score:.2f}>"


class MemorySummary(UUIDMixin, TimestampMixin, Base):
    """Periodic summaries generated from conversation windows."""

    __tablename__ = "memory_summaries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of topics as text
    message_range_start: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message_range_end: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_store_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<MemorySummary id={self.id} conv={self.conversation_id}>"
