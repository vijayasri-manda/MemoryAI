"""
Unit tests for MemoryLifecycleService logic.
Verifies evaluation rules: CREATE, UPDATE, IGNORE, REPLACE.
"""

import pytest
from app.services.memory_extraction_service import MemoryExtractionService, MemoryObject
from app.services.memory_lifecycle_service import MemoryLifecycleService


class TestMemoryLifecycleServiceRules:
    def setup_method(self):
        self.extractor = MemoryExtractionService()
        self.lifecycle = MemoryLifecycleService(db=None, vector_store=None)

    def test_ignore_duplicate_memory(self):
        old_text = "Preferred language = Java"
        new_text = "Preferred language = Java"

        extracted = self.extractor.process(new_text)
        decision = self.lifecycle.evaluate_update_rule(
            new_memory=extracted,
            existing_content=old_text,
            existing_category="Preference",
            sim_score=0.98,
        )
        assert decision == "IGNORE"

    def test_update_preference_memory(self):
        old_text = "Preferred language = Java"
        new_text = "Preferred language = Python"

        extracted = self.extractor.process(new_text)
        decision = self.lifecycle.evaluate_update_rule(
            new_memory=extracted,
            existing_content=old_text,
            existing_category="Preference",
            sim_score=0.88,
        )
        assert decision == "UPDATE"

    def test_create_new_distinct_project(self):
        old_text = "Building Hospital Management System"
        new_text = "Building MemoraAI"

        extracted = self.extractor.process(new_text)
        decision = self.lifecycle.evaluate_update_rule(
            new_memory=extracted,
            existing_content=old_text,
            existing_category="Project",
            sim_score=0.45,
        )
        assert decision == "CREATE"

    def test_update_learning_memory(self):
        old_text = "Currently learning LangChain"
        new_text = "Currently learning LangGraph"

        extracted = self.extractor.process(new_text)
        decision = self.lifecycle.evaluate_update_rule(
            new_memory=extracted,
            existing_content=old_text,
            existing_category="Learning",
            sim_score=0.82,
        )
        assert decision == "UPDATE"

    def test_replace_temporary_memory(self):
        old_text = "Currently working on this task today"
        new_text = "Working on a different temporary task right now"

        extracted = self.extractor.process(new_text)
        decision = self.lifecycle.evaluate_update_rule(
            new_memory=extracted,
            existing_content=old_text,
            existing_category="Temporary",
            sim_score=0.60,
        )
        assert decision == "REPLACE"
