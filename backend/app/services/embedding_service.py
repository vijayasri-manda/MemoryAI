"""
Embedding service abstraction and implementations.
Supports sentence-transformers (local), OpenAI, and Instructor XL.
"""

from abc import ABC, abstractmethod
from typing import Union

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Abstract Base ──────────────────────────────────────────────────────────────

class BaseEmbeddingService(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts efficiently."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...


# ── Sentence Transformers (local, free) ───────────────────────────────────────

class SentenceTransformerEmbedding(BaseEmbeddingService):
    """
    Local embedding via sentence-transformers.
    Default model: all-MiniLM-L6-v2 (384 dims, fast, good quality).
    """

    def __init__(self) -> None:
        self._model = None
        self._model_name = settings.EMBEDDING_MODEL

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # lazy import
            logger.info("Loading sentence-transformers model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name)

    async def embed_text(self, text: str) -> list[float]:
        import asyncio
        self._load()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self._model.encode(text, normalize_embeddings=True).tolist()
        )
        return result

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        self._load()
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist(),
        )
        return results

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


# ── Gemini Embeddings ──────────────────────────────────────────────────────────

class GeminiEmbeddingService(BaseEmbeddingService):
    """
    Google Gemini text-embedding-004.
    """

    def __init__(self) -> None:
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for Gemini embeddings.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model_name = settings.EMBEDDING_MODEL if "embedding" in settings.EMBEDDING_MODEL else "models/text-embedding-004"

    async def embed_text(self, text: str) -> list[float]:
        import asyncio
        import google.generativeai as genai
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None, lambda: genai.embed_content(model=self._model_name, content=text)
            )
            return res["embedding"]
        except Exception as e:
            raise EmbeddingError(f"Gemini embedding failed: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        import google.generativeai as genai
        try:
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None, lambda: genai.embed_content(model=self._model_name, content=texts)
            )
            return res["embedding"]
        except Exception as e:
            raise EmbeddingError(f"Gemini batch embedding failed: {e}") from e

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


# ── OpenAI Embeddings ──────────────────────────────────────────────────────────

class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    OpenAI text-embedding-3-small / text-embedding-3-large / ada-002.
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise EmbeddingError("OPENAI_API_KEY is required for OpenAI embeddings.")
        import openai
        self._client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._model_name = settings.EMBEDDING_MODEL or "text-embedding-3-small"

    async def embed_text(self, text: str) -> list[float]:
        try:
            response = await self._client.embeddings.create(
                input=[text], model=self._model_name
            )
            return response.data[0].embedding
        except Exception as e:
            raise EmbeddingError(f"OpenAI embedding failed: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(
                input=texts, model=self._model_name
            )
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            raise EmbeddingError(f"OpenAI batch embedding failed: {e}") from e

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


# ── Factory ───────────────────────────────────────────────────────────────────

_embedding_instance: BaseEmbeddingService | None = None


def get_embedding_service() -> BaseEmbeddingService:
    """Return the configured embedding service (singleton)."""
    global _embedding_instance
    if _embedding_instance is None:
        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider == "sentence_transformers":
            _embedding_instance = SentenceTransformerEmbedding()
        elif provider in ("gemini", "google"):
            _embedding_instance = GeminiEmbeddingService()
        elif provider == "openai":
            _embedding_instance = OpenAIEmbeddingService()
        else:
            raise EmbeddingError(f"Unknown embedding provider: {provider}")
    return _embedding_instance
