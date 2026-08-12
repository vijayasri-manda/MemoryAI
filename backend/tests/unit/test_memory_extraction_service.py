"""
Unit tests for MemoryExtractionService.
Verifies filtering of greetings, thank yous, small talk, acknowledgements,
and correct categorization into Preference, Project, Learning, Coding, Personal, Goal, and Temporary.
"""

import pytest
from app.services.memory_extraction_service import MemoryExtractionService, CATEGORY_IMPORTANCE_SCORES


class TestMemoryExtractionService:
    def setup_method(self):
        self.service = MemoryExtractionService(min_word_count=3)

    @pytest.mark.parametrize(
        "noise_text",
        [
            "Hi!",
            "Hello there",
            "Good morning",
            "Thanks!",
            "Thank you so much",
            "ok",
            "sure",
            "got it",
            "sounds good",
            "how are you?",
            "lol",
            "haha",
            "👍",
        ],
    )
    def test_ignores_noise(self, noise_text: str):
        is_noise, reason = self.service.is_noise(noise_text)
        assert is_noise is True
        assert len(reason) > 0

        res = self.service.process(noise_text)
        assert res.is_worth_storing is False
        assert res.importance == 0.0
        assert res.confidence == 0.0

    def test_stores_project(self):
        text = "I am building MemoraAI using FastAPI and React."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Project"
        assert res.importance == 0.90
        assert res.confidence > 0.80
        assert "FastAPI" in res.tags or "React" in res.tags

    def test_stores_preference(self):
        text = "My favorite language is Python."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Preference"
        assert res.importance == 0.95
        assert "Python" in res.tags

    def test_stores_goal(self):
        text = "I want to become an AI Engineer."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Goal"
        assert res.importance == 0.90

    def test_stores_coding(self):
        text = "I decided to use PostgreSQL and FastAPI for backend development."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Coding"
        assert res.importance == 0.85
        assert "PostgreSQL" in res.tags or "FastAPI" in res.tags

    def test_stores_learning(self):
        text = "I just finished studying machine learning and LLMs."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Learning"
        assert res.importance == 0.80

    def test_stores_personal(self):
        text = "My name is Alex and I live in San Francisco."
        res = self.service.process(text)
        assert res.is_worth_storing is True
        assert res.category == "Personal"
        assert res.importance == 0.85

    def test_memory_object_dict_format(self):
        text = "I am building MemoraAI using FastAPI."
        res = self.service.process(text)
        d = res.to_dict()
        assert "content" in d
        assert "category" in d
        assert "importance" in d
        assert "confidence" in d
        assert "tags" in d
        assert "created_at" in d
        assert d["source"] == "conversation"
