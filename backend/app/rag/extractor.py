"""
Memory extractor: filters and scores conversation chunks for memory-worthiness.
Uses MemoryExtractionService to evaluate messages and generate structured memories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.memory_extraction_service import (
    MemoryExtractionService,
    MemoryObject,
)

MemoryType = Literal["general", "preference", "project", "goal", "decision", "skill"]


@dataclass
class ExtractedMemory:
    content: str
    memory_type: MemoryType
    importance_score: float
    tags: list[str]


class MemoryExtractor:
    """
    Analyses text chunks and decides whether they're worth storing as memories.
    Uses MemoryExtractionService to evaluate messages, filter out noise,
    assign importance scores (0.0–1.0), and classify memory types.
    """

    def __init__(self, min_tokens: int = 20) -> None:
        self.min_tokens = min_tokens
        self.service = MemoryExtractionService(min_word_count=max(3, min_tokens // 4))

    def should_skip(self, text: str) -> bool:
        """Return True if the text is noise or not worth storing."""
        is_noise, _ = self.service.is_noise(text)
        return is_noise

    def classify_type(self, text: str) -> MemoryType:
        """Classify the memory type."""
        cat = self.service.classify_category(text)
        mapping: dict[str, MemoryType] = {
            "Preference": "preference",
            "Project": "project",
            "Goal": "goal",
            "Coding": "decision",
            "Learning": "skill",
            "Personal": "general",
            "Temporary": "general",
            "General": "general",
        }
        return mapping.get(cat, "general")

    def score_importance(self, text: str) -> float:
        """Score importance between 0.0 and 1.0."""
        cat = self.service.classify_category(text)
        return self.service.calculate_importance(cat)

    def extract_tags(self, text: str) -> list[str]:
        """Extract tags from the text."""
        cat = self.service.classify_category(text)
        raw_tags = self.service.extract_tags(text, cat)
        return [t.lower() for t in raw_tags]

    def extract(self, text: str) -> ExtractedMemory | None:
        """
        Full extraction pipeline using MemoryExtractionService.
        Returns None if the text should be skipped.
        """
        structured: MemoryObject = self.service.process(text)
        if not structured.is_worth_storing or structured.importance <= 0.0:
            return None

        mem_type = self.classify_type(text)
        return ExtractedMemory(
            content=structured.content,
            memory_type=mem_type,
            importance_score=structured.importance,
            tags=structured.tags,
        )

