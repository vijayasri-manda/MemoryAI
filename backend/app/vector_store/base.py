"""
Abstract base class for all vector store implementations.
Defines the contract every vector store must satisfy.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VectorDocument:
    """A document to be stored in the vector store."""
    id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single result from a similarity search."""
    id: str
    content: str
    metadata: dict[str, Any]
    similarity_score: float


class BaseVectorStore(ABC):
    """
    Abstract interface for vector store backends.
    All implementations must be thread-safe and async-compatible.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the connection / index. Called once at startup."""
        ...

    @abstractmethod
    async def add_documents(self, documents: list[VectorDocument]) -> list[str]:
        """
        Store documents with their embeddings.
        Returns list of stored document IDs.
        """
        ...

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        """
        Find the top_k most similar documents to the query embedding.
        Optionally filter by metadata fields.
        """
        ...

    @abstractmethod
    async def delete_documents(self, ids: list[str]) -> None:
        """Remove documents by their IDs."""
        ...

    @abstractmethod
    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        """Retrieve a document by its ID."""
        ...

    @abstractmethod
    async def update_document(self, document: VectorDocument) -> None:
        """Update a document's content, embedding, and/or metadata."""
        ...

    @abstractmethod
    async def count(self, filter_metadata: Optional[dict[str, Any]] = None) -> int:
        """Count documents, optionally filtered by metadata."""
        ...

    @abstractmethod
    async def clear_collection(self) -> None:
        """Delete ALL documents in the collection. Use with caution."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the vector store is reachable and healthy."""
        ...

    async def close(self) -> None:
        """Clean up resources. Override if needed."""
        pass
