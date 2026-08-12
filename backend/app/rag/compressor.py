"""
Context compressor: trims retrieved memory chunks to fit within the token budget.
Truncates lower-ranked chunks and summarizes if necessary.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.reranker import RankedResult

logger = get_logger(__name__)


def _token_estimate(text: str) -> int:
    return max(1, len(text) // 4)


class ContextCompressor:
    """
    Compresses retrieved memories to fit within RAG_MAX_CONTEXT_TOKENS budget.
    Strategy:
      1. Sort by rerank_score (highest first).
      2. Include full chunks until budget is exceeded.
      3. Truncate the last chunk that partially fits.
      4. Drop remaining chunks.
    """

    def __init__(self, max_tokens: int = settings.RAG_MAX_CONTEXT_TOKENS) -> None:
        self.max_tokens = max_tokens

    def compress(self, results: list[RankedResult]) -> list[str]:
        """
        Return a list of memory strings that fit within the token budget.
        Results must already be sorted by relevance (highest first).
        """
        compressed: list[str] = []
        tokens_used = 0

        for ranked in results:
            content = ranked.search_result.content.strip()
            chunk_tokens = _token_estimate(content)

            if tokens_used + chunk_tokens <= self.max_tokens:
                compressed.append(content)
                tokens_used += chunk_tokens
            else:
                # Try to fit a truncated version of this chunk
                remaining_tokens = self.max_tokens - tokens_used
                if remaining_tokens > 50:   # only worth including if >50 tokens remain
                    # Truncate at word boundary
                    words = content.split()
                    truncated_words = words[: remaining_tokens * 4 // 5]  # conservative
                    if truncated_words:
                        truncated = " ".join(truncated_words) + "..."
                        compressed.append(truncated)
                        tokens_used += _token_estimate(truncated)
                break   # stop processing further chunks

        logger.debug(
            "Context compressed",
            chunks_included=len(compressed),
            total_results=len(results),
            tokens_used=tokens_used,
            budget=self.max_tokens,
        )
        return compressed
