"""
Unit tests for the RAG chunker.
"""

import pytest
from app.rag.chunker import TextChunker, _estimate_tokens


class TestTokenEstimate:
    def test_empty_string(self):
        assert _estimate_tokens("") == 1

    def test_typical_sentence(self):
        text = "This is a typical sentence with ten words total."
        result = _estimate_tokens(text)
        assert result > 0


class TestTextChunker:
    def setup_method(self):
        self.chunker = TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_tokens=5)

    def test_empty_text(self):
        assert self.chunker.chunk("") == []

    def test_short_text_below_minimum(self):
        """Very short texts should return empty list."""
        chunks = self.chunker.chunk("Hi")
        assert chunks == []

    def test_single_chunk_for_short_text(self):
        text = "I am working on a Python FastAPI project for building a memory-augmented LLM application."
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].content == text.strip()

    def test_multiple_chunks_for_long_text(self):
        """A very long text should be split into multiple chunks."""
        long_text = " ".join([f"Sentence number {i} is about technology and machine learning." for i in range(50)])
        chunks = self.chunker.chunk(long_text)
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_metadata_propagation(self):
        text = "I prefer Python over JavaScript for backend development because it has better libraries."
        meta = {"user_id": "test-user", "session": "abc"}
        chunks = self.chunker.chunk(text, metadata=meta)
        assert len(chunks) >= 1
        assert chunks[0].metadata["user_id"] == "test-user"

    def test_chunk_messages(self):
        messages = [
            {"role": "user", "content": "I am building a RAG application using FastAPI and ChromaDB."},
            {"role": "assistant", "content": "That sounds great! What embedding model are you planning to use?"},
        ]
        chunks = self.chunker.chunk_messages(messages)
        assert len(chunks) >= 1
        assert "User:" in chunks[0].content or "user" in chunks[0].content.lower()
