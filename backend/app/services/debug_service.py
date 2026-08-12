"""
Debug Service: Captures, stores, and exposes RAG pipeline telemetry and explainability traces.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# User trace cache: user_id -> List[dict] (max 50 per user)
_USER_TRACES: Dict[str, List[dict]] = {}


class DebugService:
    """
    Stores and manages RAG explainability traces including:
    - User query, timestamp, embedding info
    - Retrieved conversation summaries and similarity scores
    - Retrieved granular memories, categories, scores, and ranking breakdown
    - Final prompt constructed
    - Gemini model response metadata and latencies
    """

    @staticmethod
    def record_trace(user_id: str, trace: dict) -> dict:
        if "id" not in trace:
            trace["id"] = str(uuid.uuid4())
        if "timestamp" not in trace:
            trace["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        trace["user_id"] = str(user_id)

        if user_id not in _USER_TRACES:
            _USER_TRACES[user_id] = []

        # Keep last 50 traces per user
        _USER_TRACES[user_id].insert(0, trace)
        if len(_USER_TRACES[user_id]) > 50:
            _USER_TRACES[user_id] = _USER_TRACES[user_id][:50]

        logger.info("RAG Debug trace recorded", trace_id=trace["id"], user_id=user_id)
        return trace

    @staticmethod
    def get_latest_trace(user_id: str) -> Optional[dict]:
        traces = _USER_TRACES.get(str(user_id), [])
        return traces[0] if traces else None

    @staticmethod
    def get_conversation_traces(user_id: str, conversation_id: str) -> List[dict]:
        user_traces = _USER_TRACES.get(str(user_id), [])
        return [t for t in user_traces if str(t.get("conversation_id")) == str(conversation_id)]

    @staticmethod
    def get_trace_by_id(user_id: str, trace_id: str) -> Optional[dict]:
        user_traces = _USER_TRACES.get(str(user_id), [])
        for t in user_traces:
            if t.get("id") == str(trace_id):
                return t
        return None
