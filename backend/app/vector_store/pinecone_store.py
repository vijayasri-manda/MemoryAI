"""
Pinecone vector store implementation.
Requires PINECONE_API_KEY and PINECONE_ENVIRONMENT in config.
"""

import asyncio
from typing import Any, Optional

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger
from app.vector_store.base import BaseVectorStore, SearchResult, VectorDocument

logger = get_logger(__name__)


class PineconeVectorStore(BaseVectorStore):
    """
    Pinecone implementation using the pinecone-client v3+ SDK.
    """

    def __init__(self) -> None:
        self._index = None

    async def initialize(self) -> None:
        if not settings.PINECONE_API_KEY:
            raise VectorStoreError("PINECONE_API_KEY is required for Pinecone vector store.")

        loop = asyncio.get_event_loop()

        def _init():
            from pinecone import Pinecone, ServerlessSpec  # type: ignore

            pc = Pinecone(api_key=settings.PINECONE_API_KEY)

            existing = [idx.name for idx in pc.list_indexes()]
            if settings.PINECONE_INDEX_NAME not in existing:
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

            return pc.Index(settings.PINECONE_INDEX_NAME)

        self._index = await loop.run_in_executor(None, _init)
        logger.info("Pinecone initialized", index=settings.PINECONE_INDEX_NAME)

    async def add_documents(self, documents: list[VectorDocument]) -> list[str]:
        if not documents:
            return []

        loop = asyncio.get_event_loop()
        vectors = [
            {
                "id": d.id,
                "values": d.embedding,
                "metadata": {**d.metadata, "content": d.content},
            }
            for d in documents
        ]

        await loop.run_in_executor(None, lambda: self._index.upsert(vectors=vectors))
        return [d.id for d in documents]

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _query():
            return self._index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filter_metadata,
                include_metadata=True,
            )

        response = await loop.run_in_executor(None, _query)

        results = []
        for match in response.matches:
            if match.score < score_threshold:
                continue
            metadata = dict(match.metadata or {})
            content = metadata.pop("content", "")
            results.append(
                SearchResult(
                    id=match.id,
                    content=content,
                    metadata=metadata,
                    similarity_score=match.score,
                )
            )
        return results

    async def delete_documents(self, ids: list[str]) -> None:
        if not ids:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._index.delete(ids=ids))

    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._index.fetch(ids=[doc_id])
        )
        vectors = result.vectors
        if doc_id not in vectors:
            return None
        vec = vectors[doc_id]
        metadata = dict(vec.metadata or {})
        content = metadata.pop("content", "")
        return VectorDocument(
            id=doc_id, content=content, embedding=list(vec.values), metadata=metadata
        )

    async def update_document(self, document: VectorDocument) -> None:
        await self.add_documents([document])

    async def count(self, filter_metadata: Optional[dict[str, Any]] = None) -> int:
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, self._index.describe_index_stats)
        return stats.total_vector_count

    async def clear_collection(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._index.delete(delete_all=True))

    async def health_check(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._index.describe_index_stats)
            return True
        except Exception as e:
            logger.error("Pinecone health check failed", error=str(e))
            return False
