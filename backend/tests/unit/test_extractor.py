"""
Unit tests for the memory extractor.
"""

import pytest
from app.rag.extractor import MemoryExtractor


class TestMemoryExtractor:
    def setup_method(self):
        self.extractor = MemoryExtractor(min_tokens=5)

    def test_skip_greeting(self):
        assert self.extractor.should_skip("Hello!") is True
        assert self.extractor.should_skip("hi") is True
        assert self.extractor.should_skip("Thanks!") is True
        assert self.extractor.should_skip("ok") is True

    def test_skip_empty(self):
        assert self.extractor.should_skip("") is True

    def test_should_not_skip_technical_content(self):
        text = "I am building a FastAPI application with PostgreSQL and Redis for caching."
        assert self.extractor.should_skip(text) is False

    def test_classify_preference(self):
        text = "I prefer Python and usually use FastAPI for building REST APIs."
        result = self.extractor.classify_type(text)
        assert result == "preference"

    def test_classify_project(self):
        text = "I am working on a machine learning project using LangChain and ChromaDB."
        result = self.extractor.classify_type(text)
        assert result == "project"

    def test_classify_goal(self):
        text = "My goal is to learn deep learning and eventually build my own LLM."
        result = self.extractor.classify_type(text)
        assert result == "goal"

    def test_classify_decision(self):
        text = "I decided to go with PostgreSQL instead of MongoDB for the database."
        result = self.extractor.classify_type(text)
        assert result == "decision"

    def test_importance_score_range(self):
        technical_text = "I am building a RAG system with FAISS, working on a project deadline."
        score = self.extractor.score_importance(technical_text)
        assert 0.0 <= score <= 1.0

    def test_high_importance_for_technical_content(self):
        rich_text = (
            "My main project is building an AI assistant using RAG and LangChain. "
            "I prefer Python, and my goal is to deploy it on AWS with Kubernetes. "
            "I decided to use PostgreSQL and ChromaDB. I am experienced with FastAPI "
            "and working on the embedding service this week."
        )
        score = self.extractor.score_importance(rich_text)
        assert score > 0.5

    def test_extract_tags(self):
        text = "I love Python and I am working on a FastAPI project with PostgreSQL."
        tags = self.extractor.extract_tags(text)
        assert "python" in tags
        assert "fastapi" in tags

    def test_extract_returns_none_for_greeting(self):
        result = self.extractor.extract("Hello!")
        assert result is None

    def test_extract_returns_memory_for_technical(self):
        text = "I prefer Python over Java and I am working on a data pipeline project."
        result = self.extractor.extract(text)
        assert result is not None
        assert result.content == text.strip()
        assert result.memory_type in ("preference", "project", "general")
        assert 0.0 <= result.importance_score <= 1.0
