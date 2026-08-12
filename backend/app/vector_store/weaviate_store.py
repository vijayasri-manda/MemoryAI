"""
Weaviate vector store implementation.

NOTE: Weaviate support is a stub. To enable it, install the `weaviate-client`
package and implement the methods below following the same interface as
ChromaVectorStore or FAISSVectorStore.
"""

from __future__ import annotations

from app.core.exceptions import VectorStoreError
from app.vector_store.base import BaseVectorStore


class WeaviateVectorStore(BaseVectorStore):
    """
    Weaviate-backed vector store (not yet implemented).

    Install `weaviate-client` and implement this class to enable Weaviate
    support. See https://weaviate.io/developers/weaviate/client-libraries/python
    """

    async def initialize(self) -> None:
        raise VectorStoreError(
            "Weaviate vector store is not implemented. "
            "Please choose 'chroma', 'faiss', or 'pinecone' as VECTOR_STORE_TYPE."
        )

    async def add_documents(self, documents, embeddings, metadatas=None, ids=None):
        raise VectorStoreError("Weaviate vector store is not implemented.")

    async def search(self, query_embedding, top_k: int = 5, filter_dict=None):
        raise VectorStoreError("Weaviate vector store is not implemented.")

    async def delete(self, ids) -> None:
        raise VectorStoreError("Weaviate vector store is not implemented.")

    async def close(self) -> None:
        pass
