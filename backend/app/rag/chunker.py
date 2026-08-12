"""
Text chunker: splits conversation text into semantic, token-aware chunks.
Uses sentence-boundary-aware splitting with configurable window and overlap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_estimate: int = 0
    metadata: dict = field(default_factory=dict)


def _estimate_tokens(text: str) -> int:
    """Fast approximation: 1 token ≈ 4 characters for English text."""
    return max(1, len(text) // 4)


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using regex (avoids NLTK dependency at runtime)."""
    # Split on sentence-ending punctuation followed by whitespace
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


class TextChunker:
    """
    Splits long texts into overlapping chunks that respect sentence boundaries.
    Strategy:
      1. Split into sentences.
      2. Greedily accumulate sentences until chunk_size tokens is reached.
      3. Slide the window forward, keeping `chunk_overlap` tokens of context.
    """

    def __init__(
        self,
        chunk_size: int = settings.RAG_CHUNK_SIZE,
        chunk_overlap: int = settings.RAG_CHUNK_OVERLAP,
        min_chunk_tokens: int = settings.MEMORY_MIN_TOKENS,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_tokens = min_chunk_tokens

    def chunk(self, text: str, metadata: dict | None = None) -> list[TextChunk]:
        """Split text into chunks. Returns empty list for texts below minimum size."""
        if not text or not text.strip():
            return []

        token_count = _estimate_tokens(text)
        if token_count < self.min_chunk_tokens:
            return []

        # If the whole text fits in one chunk, return as-is
        if token_count <= self.chunk_size:
            return [
                TextChunk(
                    content=text.strip(),
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    token_estimate=token_count,
                    metadata=metadata or {},
                )
            ]

        sentences = _split_into_sentences(text)
        chunks: list[TextChunk] = []
        current_sentences: list[str] = []
        current_tokens = 0
        char_offset = 0
        chunk_idx = 0

        for sentence in sentences:
            sent_tokens = _estimate_tokens(sentence)

            if current_tokens + sent_tokens > self.chunk_size and current_sentences:
                # Emit current chunk
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        chunk_index=chunk_idx,
                        start_char=char_offset,
                        end_char=char_offset + len(chunk_text),
                        token_estimate=current_tokens,
                        metadata=metadata or {},
                    )
                )
                chunk_idx += 1

                # Roll back by overlap: keep sentences until we're under overlap budget
                overlap_tokens = 0
                overlap_sentences: list[str] = []
                for s in reversed(current_sentences):
                    s_tok = _estimate_tokens(s)
                    if overlap_tokens + s_tok > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tok

                char_offset += len(chunk_text) - sum(len(s) + 1 for s in overlap_sentences)
                current_sentences = overlap_sentences
                current_tokens = overlap_tokens

            current_sentences.append(sentence)
            current_tokens += sent_tokens

        # Emit remaining
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            if _estimate_tokens(chunk_text) >= self.min_chunk_tokens:
                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        chunk_index=chunk_idx,
                        start_char=char_offset,
                        end_char=char_offset + len(chunk_text),
                        token_estimate=current_tokens,
                        metadata=metadata or {},
                    )
                )

        return chunks

    def chunk_messages(
        self, messages: list[dict], metadata: dict | None = None
    ) -> list[TextChunk]:
        """
        Chunk a list of chat messages (role/content dicts).
        Formats as 'Role: Content' and splits into chunks.
        """
        combined = "\n\n".join(
            f"{m['role'].capitalize()}: {m['content']}"
            for m in messages
            if m.get("content")
        )
        return self.chunk(combined, metadata=metadata)
