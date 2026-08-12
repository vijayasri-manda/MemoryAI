"""
Deduplicator: removes semantically duplicate memories from retrieved results.
Uses cosine similarity on already-computed embeddings.
"""

from __future__ import annotations

import numpy as np

from app.core.config import settings
from app.rag.reranker import RankedResult


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Fast cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class Deduplicator:
    """
    Removes near-duplicate memories using cosine similarity threshold.
    When two memories are too similar, the one with the higher rerank score
    is retained.
    """

    def __init__(self, threshold: float = settings.RAG_DEDUPE_THRESHOLD) -> None:
        self.threshold = threshold

    def deduplicate(
        self,
        results: list[RankedResult],
        embeddings: dict[str, list[float]] | None = None,
    ) -> list[RankedResult]:
        """
        Remove duplicate results.
        If embeddings dict is provided, uses cosine similarity for deduplication.
        Falls back to exact string matching otherwise.
        """
        if not results:
            return []

        kept: list[RankedResult] = []

        for candidate in results:
            is_duplicate = False
            cand_id = candidate.search_result.id
            cand_content = candidate.search_result.content.lower().strip()

            for retained in kept:
                ret_id = retained.search_result.id
                ret_content = retained.search_result.content.lower().strip()

                # Check exact content match
                if cand_content == ret_content:
                    is_duplicate = True
                    break

                # Check embedding similarity if available
                if embeddings and cand_id in embeddings and ret_id in embeddings:
                    sim = _cosine_sim(embeddings[cand_id], embeddings[ret_id])
                    if sim >= self.threshold:
                        is_duplicate = True
                        break

                # Fallback: simple character-level overlap heuristic
                if not embeddings:
                    overlap = len(set(cand_content.split()) & set(ret_content.split()))
                    union = len(set(cand_content.split()) | set(ret_content.split()))
                    jaccard = overlap / max(union, 1)
                    if jaccard >= self.threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                kept.append(candidate)

        return kept
