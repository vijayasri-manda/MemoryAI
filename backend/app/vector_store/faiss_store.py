"""
FAISS vector store implementation.
Fully local, high-performance, no external dependencies.
"""

import asyncio
import json
import os
import pickle
from typing import Any, Optional

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.vector_store.base import BaseVectorStore, SearchResult, VectorDocument

logger = get_logger(__name__)


class FAISSVectorStore(BaseVectorStore):
    """
    FAISS-backed vector store using an IndexFlatIP (inner product = cosine similarity
    when vectors are L2-normalised).
    Persists the index and metadata to disk.
    """

    def __init__(self) -> None:
        self._index = None
        self._id_map: list[str] = []          # position → document id
        self._doc_map: dict[str, dict] = {}   # id → {content, metadata}
        self._index_path = f"{settings.FAISS_INDEX_PATH}/index.faiss"
        self._meta_path = f"{settings.FAISS_INDEX_PATH}/metadata.pkl"

    async def initialize(self) -> None:
        import faiss  # lazy import

        loop = asyncio.get_event_loop()

        def _init():
            os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
            if os.path.exists(self._index_path) and os.path.exists(self._meta_path):
                index = faiss.read_index(self._index_path)
                with open(self._meta_path, "rb") as f:
                    state = pickle.load(f)
                return index, state["id_map"], state["doc_map"]
            else:
                # IndexFlatIP on L2-normalised vectors = cosine similarity
                index = faiss.IndexFlatIP(settings.EMBEDDING_DIMENSION)
                return index, [], {}

        self._index, self._id_map, self._doc_map = await loop.run_in_executor(None, _init)
        logger.info("FAISS initialized", index_path=self._index_path)

    def _save(self) -> None:
        import faiss
        faiss.write_index(self._index, self._index_path)
        with open(self._meta_path, "wb") as f:
            pickle.dump({"id_map": self._id_map, "doc_map": self._doc_map}, f)

    @staticmethod
    def _normalize(vec: list[float]) -> np.ndarray:
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr /= norm
        return arr

    async def add_documents(self, documents: list[VectorDocument]) -> list[str]:
        if not documents:
            return []

        import faiss

        loop = asyncio.get_event_loop()

        def _add():
            vectors = np.stack(
                [self._normalize(d.embedding) for d in documents]
            ).astype(np.float32)

            for doc in documents:
                if doc.id in self._doc_map:
                    # Remove old entry (FAISS doesn't support in-place update)
                    try:
                        pos = self._id_map.index(doc.id)
                        self._id_map[pos] = "__deleted__"
                    except ValueError:
                        pass
                self._doc_map[doc.id] = {"content": doc.content, "metadata": doc.metadata}

            self._index.add(vectors)
            self._id_map.extend([d.id for d in documents])
            self._save()
            return [d.id for d in documents]

        return await loop.run_in_executor(None, _add)

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        if self._index.ntotal == 0:
            return []

        loop = asyncio.get_event_loop()

        def _search():
            query = self._normalize(query_embedding).reshape(1, -1)
            k = min(top_k * 3, self._index.ntotal)  # over-fetch for filtering
            scores, indices = self._index.search(query, k)

            results = []
            seen_ids = set()
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self._id_map):
                    continue
                doc_id = self._id_map[idx]
                if doc_id == "__deleted__" or doc_id in seen_ids:
                    continue
                if score < score_threshold:
                    continue
                doc = self._doc_map.get(doc_id)
                if not doc:
                    continue

                # Apply metadata filter
                if filter_metadata:
                    meta = doc["metadata"]
                    if not all(meta.get(k) == v for k, v in filter_metadata.items()):
                        continue

                seen_ids.add(doc_id)
                results.append(
                    SearchResult(
                        id=doc_id,
                        content=doc["content"],
                        metadata=doc["metadata"],
                        similarity_score=float(score),
                    )
                )
                if len(results) >= top_k:
                    break
            return results

        return await loop.run_in_executor(None, _search)

    async def delete_documents(self, ids: list[str]) -> None:
        loop = asyncio.get_event_loop()

        def _delete():
            for doc_id in ids:
                if doc_id in self._doc_map:
                    del self._doc_map[doc_id]
                try:
                    pos = self._id_map.index(doc_id)
                    self._id_map[pos] = "__deleted__"
                except ValueError:
                    pass
            self._save()

        await loop.run_in_executor(None, _delete)

    async def get_document(self, doc_id: str) -> Optional[VectorDocument]:
        doc = self._doc_map.get(doc_id)
        if not doc:
            return None
        return VectorDocument(
            id=doc_id,
            content=doc["content"],
            embedding=[],   # FAISS doesn't store raw embeddings easily
            metadata=doc["metadata"],
        )

    async def update_document(self, document: VectorDocument) -> None:
        await self.add_documents([document])

    async def count(self, filter_metadata: Optional[dict[str, Any]] = None) -> int:
        if filter_metadata:
            return sum(
                1 for d in self._doc_map.values()
                if all(d["metadata"].get(k) == v for k, v in filter_metadata.items())
            )
        return len([id_ for id_ in self._id_map if id_ != "__deleted__"])

    async def clear_collection(self) -> None:
        import faiss
        self._index = faiss.IndexFlatIP(settings.EMBEDDING_DIMENSION)
        self._id_map = []
        self._doc_map = {}
        self._save()

    async def health_check(self) -> bool:
        return self._index is not None
