"""
ChromaDB vector store implementation.
Default store — fully local, no API keys needed.
"""

import asyncio
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger
from app.vector_store.base import BaseVectorStore, SearchResult, VectorDocument

logger = get_logger(__name__)


def _format_where(filter_metadata: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not filter_metadata:
        return None
    if any(k.startswith("$") for k in filter_metadata.keys()):
        return filter_metadata
    if len(filter_metadata) == 1:
        return filter_metadata
    return {"$and": [{k: v} for k, v in filter_metadata.items()]}


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB implementation.
    Supports both local persistent mode and remote HTTP client mode.
    """

    def __init__(self) -> None:
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    async def initialize(self) -> None:
        """Set up ChromaDB client and collection."""
        loop = asyncio.get_event_loop()

        def _init():
            if settings.CHROMA_HOST:
                # Remote ChromaDB server
                client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            else:
                # Local persistent mode
                client = chromadb.PersistentClient(
                    path=settings.CHROMA_PERSIST_DIR,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            collection = client.get_or_create_collection(
                name=settings.VECTOR_STORE_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            return client, collection

        self._client, self._collection = await loop.run_in_executor(None, _init)
        logger.info("ChromaDB initialized", collection=settings.VECTOR_STORE_COLLECTION)

    async def add_documents(self, documents: list[VectorDocument]) -> list[str]:
        if not documents:
            return []

        ids = [d.id for d in documents]
        embeddings = [d.embedding for d in documents]
        documents_text = [d.content for d in documents]
        metadatas = [d.metadata for d in documents]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas,
            ),
        )
        return ids

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        where = _format_where(filter_metadata)

        def _query():
            return self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count() or 1),
                where=where,
                include=["documents", "metadatas", "distances"],
            )

        results = await loop.run_in_executor(None, _query)

        search_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            # Chroma uses L2 distance or cosine distance (0=identical)
            # We convert distance to similarity: similarity = 1 - distance
            distance = results["distances"][0][i]
            similarity = 1.0 - distance

            if similarity < score_threshold:
                continue

            search_results.append(
                SearchResult(
                    id=doc_id,
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] or {},
                    similarity_score=similarity,
                )
            )

        return search_results

    async def delete_documents(self, ids: list[str]) -> None:
        if not ids:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._collection.delete(ids=ids))

    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        loop = asyncio.get_event_loop()

        def _get():
            return self._collection.get(
                ids=[doc_id], include=["documents", "metadatas", "embeddings"]
            )

        result = await loop.run_in_executor(None, _get)
        if not result["ids"]:
            return None

        return VectorDocument(
            id=result["ids"][0],
            content=result["documents"][0],
            embedding=result["embeddings"][0],
            metadata=result["metadatas"][0] or {},
        )

    async def update_document(self, document: VectorDocument) -> None:
        await self.add_documents([document])   # upsert handles updates

    async def count(self, filter_metadata: Optional[dict[str, Any]] = None) -> int:
        where = _format_where(filter_metadata)
        if where:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self._collection.get(where=where)
            )
            return len(result["ids"])
        return self._collection.count()

    async def clear_collection(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: self._client.delete_collection(settings.VECTOR_STORE_COLLECTION)
        )
        await self.initialize()

    async def health_check(self) -> bool:
        try:
            self._collection.count()
            return True
        except Exception as e:
            logger.error("ChromaDB health check failed", error=str(e))
            return False
