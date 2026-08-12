"""
Unit tests for SummaryService & Hierarchical Retrieval.
"""

import pytest
from app.rag.prompt_builder import PromptBuilder
from app.services.summary_service import SummaryService


class TestSummaryServiceAndPromptBuilder:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_prompt_builder_hierarchical_structure(self):
        summaries = [
            "Project: MemoraAI | Tech Stack: FastAPI, React, ChromaDB | Progress: Completed Smart Memory Extraction."
        ]
        memories = [
            "User prefers Python over Java for backend development.",
            "Career goal is becoming an AI Engineer."
        ]
        history = [
            {"role": "user", "content": "What tech stack am I using for my project?"}
        ]

        messages = self.builder.build(
            user_query="What tech stack am I using for my project?",
            conversation_history=history,
            retrieved_memories=memories,
            current_datetime="2026-08-05 13:30 UTC",
            summaries=summaries,
        )

        assert len(messages) >= 2
        system_msg = messages[0].content
        assert "CONVERSATION SUMMARIES" in system_msg
        assert "RELEVANT MEMORIES" in system_msg
        assert "MemoraAI" in system_msg
        assert "Python over Java" in system_msg

    @pytest.mark.asyncio
    async def test_summary_text_generation(self):
        history = [
            {"role": "user", "content": "I'm building MemoraAI using FastAPI and React."},
            {"role": "assistant", "content": "That sounds awesome! What database are you using?"},
            {"role": "user", "content": "I am using PostgreSQL and ChromaDB for vector storage."},
        ]

        service = SummaryService(db=None, vector_store=None)
        summary_text, topics = await service.generate_summary_text(history)

        assert isinstance(summary_text, str)
        assert len(summary_text) > 0
        assert isinstance(topics, list)
