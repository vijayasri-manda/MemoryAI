"""
Vector store factory — creates the correct implementation based on config.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.vector_store.base import BaseVectorStore

logger = get_logger(__name__)

_vector_store_instance: "BaseVectorStore | None" = None


async def get_vector_store() -> "BaseVectorStore":
    """
    FastAPI dependency / application-level singleton.
    Returns the initialized vector store instance.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = _create_vector_store()
        await _vector_store_instance.initialize()
        logger.info(
            "Vector store ready",
            type=settings.VECTOR_STORE_TYPE,
        )
    return _vector_store_instance


def _create_vector_store() -> "BaseVectorStore":
    store_type = settings.VECTOR_STORE_TYPE.lower()

    if store_type == "chroma":
        from app.vector_store.chroma_store import ChromaVectorStore
        return ChromaVectorStore()
    elif store_type == "faiss":
        from app.vector_store.faiss_store import FAISSVectorStore
        return FAISSVectorStore()
    elif store_type == "pinecone":
        from app.vector_store.pinecone_store import PineconeVectorStore
        return PineconeVectorStore()
    elif store_type == "weaviate":
        from app.vector_store.weaviate_store import WeaviateVectorStore
        return WeaviateVectorStore()
    else:
        raise VectorStoreError(f"Unknown vector store type: {store_type}")


async def close_vector_store() -> None:
    """Call on application shutdown."""
    global _vector_store_instance
    if _vector_store_instance is not None:
        await _vector_store_instance.close()
        _vector_store_instance = None
