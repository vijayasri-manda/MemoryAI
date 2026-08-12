"""
Re-ranker: re-orders retrieved memories using a cross-encoder model.
Falls back to score-based ordering when cross-encoder is unavailable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger
from app.vector_store.base import SearchResult

logger = get_logger(__name__)


@dataclass
class RankedResult:
    search_result: SearchResult
    rerank_score: float


class Reranker:
    """
    Cross-encoder re-ranker for retrieved memory chunks.
    Uses sentence-transformers cross-encoder when available,
    falls back to the original similarity score otherwise.
    """

    CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self) -> None:
        self._cross_encoder = None
        self._available = False

    def _load(self) -> None:
        if not self._available:
            try:
                from sentence_transformers import CrossEncoder  # type: ignore
                self._cross_encoder = CrossEncoder(self.CROSS_ENCODER_MODEL, max_length=512)
                self._available = True
                logger.info("Cross-encoder re-ranker loaded", model=self.CROSS_ENCODER_MODEL)
            except ImportError:
                logger.warning("sentence-transformers not available; using score-based ranking")
            except Exception as e:
                logger.warning("Cross-encoder load failed; using score-based ranking", error=str(e))

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[RankedResult]:
        """
        Re-rank a list of SearchResults against the query.
        Returns at most top_k results sorted by rerank_score descending.
        """
        if not results:
            return []

        if not settings.RAG_RERANK_ENABLED:
            ranked = [
                RankedResult(search_result=r, rerank_score=r.similarity_score) for r in results
            ]
            ranked.sort(key=lambda x: x.rerank_score, reverse=True)
            return ranked[:top_k] if top_k else ranked

        self._load()

        if self._available and self._cross_encoder:
            loop = asyncio.get_event_loop()
            pairs = [(query, r.content) for r in results]

            scores = await loop.run_in_executor(
                None, lambda: self._cross_encoder.predict(pairs)
            )

            ranked = [
                RankedResult(search_result=r, rerank_score=float(s))
                for r, s in zip(results, scores)
            ]
        else:
            # Fallback: use original similarity scores
            ranked = [
                RankedResult(search_result=r, rerank_score=r.similarity_score)
                for r in results
            ]

        ranked.sort(key=lambda x: x.rerank_score, reverse=True)
        return ranked[:top_k] if top_k else ranked
