"""
Memory Extraction Engine: Evaluates conversation messages and decides whether new long-term memories should be created.
Filters out noise (greetings, thank yous, small talk, acknowledgements) and categorizes structured memories into:
- Preference
- Project
- Learning
- Coding
- Personal
- Goal
- Temporary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal

MemoryCategory = Literal[
    "Preference",
    "Project",
    "Learning",
    "Coding",
    "Personal",
    "Goal",
    "Temporary",
    "General",
]

# ── Base Importance Scores ───────────────────────────────────────────────────

CATEGORY_IMPORTANCE_SCORES: dict[MemoryCategory, float] = {
    "Preference": 0.95,
    "Project": 0.90,
    "Goal": 0.90,
    "Coding": 0.85,
    "Personal": 0.85,
    "Learning": 0.80,
    "Temporary": 0.50,
    "General": 0.40,
}

# ── Noise Patterns to IGNORE ──────────────────────────────────────────────────

_GREETINGS_PATTERNS = [
    r"^\s*(?:hi|hello|hey|howdy|greetings|good\s+(?:morning|evening|afternoon|night))\s*[!.?]*\s*$",
    r"^\s*(?:bye|goodbye|see\s+you|later|cya)\s*[!.?]*\s*$",
]

_THANK_YOU_PATTERNS = [
    r"^\s*(?:thanks|thank\s+you|thx|ty|much\s+appreciated|thanks\s+a\s+lot)(?:\s+(?:so\s+much|very\s+much|a\s+lot))?\s*[!.?]*\s*$",
]

_SMALL_TALK_PATTERNS = [
    r"^\s*(?:how\s+are\s+you|how\s+is\s+it\s+going|what'?s\s+up|how's\s+life)\s*[!.?]*\s*$",
    r"^\s*(?:lol|lmao|haha|hehe|rofl|funny)\s*[!.?]*\s*$",
    r"^\s*(?:👍|❤️|😊|🙏|✅|😂|🔥|🎉|💯)\s*$",
]

_ACKNOWLEDGEMENT_PATTERNS = [
    r"^\s*(?:ok|okay|sure|yes|no|yep|nope|got\s+it|sounds\s+good|alright|cool|understood|k)\s*[!.?]*\s*$",
]

_ALL_IGNORE_PATTERNS = (
    _GREETINGS_PATTERNS
    + _THANK_YOU_PATTERNS
    + _SMALL_TALK_PATTERNS
    + _ACKNOWLEDGEMENT_PATTERNS
)

_IGNORE_REGEX = re.compile("|".join(_ALL_IGNORE_PATTERNS), re.IGNORECASE)


# ── Category Matchers ─────────────────────────────────────────────────────────

_CATEGORY_PATTERNS: dict[MemoryCategory, re.Pattern] = {
    "Project": re.compile(
        r"\b(?:project|app|application|system|building|developing|implement|working\s+on|repo|codebase|memoraai)\b",
        re.IGNORECASE,
    ),
    "Preference": re.compile(
        r"\b(?:prefer|preference|like|love|enjoy|hate|dislike|always\s+use|usually\s+use|favorite|favourite|style)\b",
        re.IGNORECASE,
    ),
    "Goal": re.compile(
        r"\b(?:goal|objective|want\s+to|aim\s+to|hope\s+to|plan\s+to|target|aspire|milestone|become)\b",
        re.IGNORECASE,
    ),
    "Coding": re.compile(
        r"\b(?:decided|chose|chosen|going\s+with|selected|architecture|pattern|tech\s+stack|code|fastapi|react|python|postgresql|sqlite|redis|chroma|docker|git)\b",
        re.IGNORECASE,
    ),
    "Learning": re.compile(
        r"\b(?:learned|learning|studying|mastering|understanding|course|tutorial|practicing|practiced|read\s+about)\b",
        re.IGNORECASE,
    ),
    "Personal": re.compile(
        r"\b(?:my\s+name|i\s+am|my\s+role|my\s+job|my\s+title|company|family|city|live\s+in|work\s+at)\b",
        re.IGNORECASE,
    ),
    "Temporary": re.compile(
        r"\b(?:today|tomorrow|this\s+week|currently|temporary|right\s+now|for\s+now|now)\b",
        re.IGNORECASE,
    ),
}


@dataclass
class MemoryObject:
    """
    Structured Memory Object matching specification:
    {
        "content": "...",
        "category": "...",
        "importance": 0.0,
        "confidence": 0.0,
        "tags": [],
        "created_at": "...",
        "source": "conversation"
    }
    """

    content: str
    category: MemoryCategory
    importance: float
    confidence: float
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    source: str = "conversation"
    is_worth_storing: bool = True
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "confidence": self.confidence,
            "tags": self.tags,
            "created_at": self.created_at,
            "source": self.source,
        }


class MemoryExtractionService:
    """
    Memory Extraction Engine:
    Analyzes messages and determines whether new long-term memories should be created.
    """

    def __init__(self, min_word_count: int = 3) -> None:
        self.min_word_count = min_word_count

    def is_noise(self, text: str) -> tuple[bool, str]:
        """
        Check if text matches noise patterns (greetings, thank yous, acknowledgements).
        """
        stripped = text.strip()
        if not stripped:
            return True, "Empty content"

        words = stripped.split()
        if len(words) < self.min_word_count and not any(
            c in stripped.lower() for c in ["python", "fastapi", "react", "rag", "sql"]
        ):
            return True, "Content too short / low information density"

        if _IGNORE_REGEX.match(stripped):
            return True, "Ignored: greeting, thank you, small talk, or short acknowledgement"

        return False, ""

    def classify_category(self, text: str) -> MemoryCategory:
        """Classify text into one of the key memory categories."""
        match_counts: dict[MemoryCategory, int] = {cat: 0 for cat in _CATEGORY_PATTERNS}
        for category, pattern in _CATEGORY_PATTERNS.items():
            match_counts[category] = len(pattern.findall(text))

        best_category = max(match_counts, key=lambda k: match_counts[k])
        if match_counts[best_category] > 0:
            return best_category
        return "General"

    def calculate_importance(self, category: MemoryCategory) -> float:
        """Assign importance score based on category."""
        return CATEGORY_IMPORTANCE_SCORES.get(category, 0.40)

    def calculate_confidence(self, text: str, category: MemoryCategory) -> float:
        """Calculate confidence score (0.0 to 1.0) for the extraction."""
        pattern = _CATEGORY_PATTERNS.get(category)
        if not pattern:
            return 0.70

        matches = len(pattern.findall(text))
        if matches >= 2:
            return 0.95
        elif matches == 1:
            return 0.88
        return 0.75

    def extract_tags(self, text: str, category: MemoryCategory) -> list[str]:
        """Auto-generate useful tags for the memory."""
        tags = []
        tech_keywords = [
            "FastAPI", "React", "Python", "TypeScript", "JavaScript",
            "PostgreSQL", "SQLite", "ChromaDB", "FAISS", "Redis",
            "Docker", "Kubernetes", "LLM", "RAG", "LangChain", "OpenAI", "Gemini"
        ]
        text_lower = text.lower()
        for kw in tech_keywords:
            if kw.lower() in text_lower:
                tags.append(kw)

        if category not in tags and category != "General":
            tags.insert(0, category)

        return list(set(tags))

    def process(self, text: str) -> MemoryObject:
        """
        Process text and generate a structured MemoryObject.
        """
        is_noise_flag, reason = self.is_noise(text)
        if is_noise_flag:
            return MemoryObject(
                content=text.strip(),
                category="General",
                importance=0.00,
                confidence=0.00,
                tags=[],
                is_worth_storing=False,
                reason=reason,
            )

        category = self.classify_category(text)
        importance = self.calculate_importance(category)
        confidence = self.calculate_confidence(text, category)
        tags = self.extract_tags(text, category)

        return MemoryObject(
            content=text.strip(),
            category=category,
            importance=importance,
            confidence=confidence,
            tags=tags,
            is_worth_storing=True,
            reason=f"Valid {category} memory",
        )
