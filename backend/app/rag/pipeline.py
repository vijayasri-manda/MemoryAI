"""
Full RAG pipeline: orchestrates the entire memory retrieval → prompt injection cycle.
This is the central coordinator of the AI memory system.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.chunker import TextChunker
from app.rag.compressor import ContextCompressor
from app.rag.deduplicator import Deduplicator
from app.rag.extractor import MemoryExtractor
from app.rag.prompt_builder import PromptBuilder
from app.rag.reranker import Reranker
from app.services.embedding_service import get_embedding_service
from app.vector_store.base import VectorDocument

if TYPE_CHECKING:
    from app.vector_store.base import BaseVectorStore
    from app.services.llm_service import BaseLLMService, ChatMessage

logger = get_logger(__name__)


class RAGPipeline:
    """
    The core RAG pipeline for AI memory.

    Store Pipeline (after conversation):
      messages → chunk → extract → embed → store in vector DB + postgres

    Retrieve Pipeline (before LLM call):
      query → embed → similarity search → rerank → deduplicate → compress → inject
    """

    def __init__(self, vector_store: "BaseVectorStore") -> None:
        self.vector_store = vector_store
        self.chunker = TextChunker()
        self.extractor = MemoryExtractor()
        self.reranker = Reranker()
        self.deduplicator = Deduplicator()
        self.compressor = ContextCompressor()
        self.prompt_builder = PromptBuilder()

    # ── STORE ──────────────────────────────────────────────────────────────────

    async def store_memories(
        self,
        messages: list[dict],
        user_id: str,
        conversation_id: str,
        session_metadata: dict | None = None,
    ) -> list[dict]:
        """
        Extract meaningful memories from conversation messages and store them.

        Returns list of memory metadata dicts (for postgres insertion).
        """
        embedding_service = get_embedding_service()
        stored_memories = []

        base_metadata = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            **(session_metadata or {}),
        }

        # Chunk conversation
        chunks = self.chunker.chunk_messages(messages, metadata=base_metadata)
        logger.info(
            "Memory storage started", chunks=len(chunks), conversation_id=conversation_id
        )

        # Filter and score chunks
        to_embed: list[tuple] = []   # (chunk_text, chunk_idx, extracted_memory)
        for chunk in chunks:
            extracted = self.extractor.extract(chunk.content)
            if extracted is None:
                continue
            if extracted.importance_score < settings.MEMORY_IMPORTANCE_THRESHOLD:
                continue
            to_embed.append((chunk.content, chunk.chunk_index, extracted))

        if not to_embed:
            logger.info("No memories worth storing", conversation_id=conversation_id)
            return []

        # Batch embed
        texts = [t[0] for t in to_embed]
        embeddings = await embedding_service.embed_batch(texts)

        # Build vector documents
        vector_docs = []
        for (content, chunk_idx, extracted), embedding in zip(to_embed, embeddings):
            memory_id = str(uuid.uuid4())

            # Compute expiry
            expires_at = None
            if settings.MEMORY_TTL_DAYS > 0:
                from datetime import timedelta
                expires_at = (
                    datetime.now(tz=timezone.utc) + timedelta(days=settings.MEMORY_TTL_DAYS)
                ).isoformat()

            vector_doc = VectorDocument(
                id=memory_id,
                content=content,
                embedding=embedding,
                metadata={
                    **base_metadata,
                    "memory_type": extracted.memory_type,
                    "importance_score": extracted.importance_score,
                    "tags": json.dumps(extracted.tags),
                    "chunk_index": chunk_idx,
                    "embedding_model": settings.EMBEDDING_MODEL,
                },
            )
            vector_docs.append(vector_doc)

            stored_memories.append(
                {
                    "id": memory_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "content": content,
                    "memory_type": extracted.memory_type,
                    "importance_score": extracted.importance_score,
                    "tags": json.dumps(extracted.tags),
                    "chunk_index": chunk_idx,
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "expires_at": expires_at,
                    "vector_store_id": memory_id,
                }
            )

        # Store in vector DB
        await self.vector_store.add_documents(vector_docs)
        logger.info(
            "Memories stored",
            count=len(stored_memories),
            conversation_id=conversation_id,
        )
        return stored_memories

    # ── RETRIEVE ──────────────────────────────────────────────────────────────

    async def retrieve_memories(
        self,
        query: str,
        user_id: str,
        top_k: int = settings.RAG_TOP_K,
    ) -> list[str]:
        """
        Full retrieval pipeline: embed → search → rerank → deduplicate → compress.

        Returns a list of memory strings ready for prompt injection.
        """
        embedding_service = get_embedding_service()

        # 1. Embed query
        query_embedding = await embedding_service.embed_text(query)

        # 2. Semantic search (filter by user to ensure isolation)
        raw_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k * 3,   # over-fetch for reranking/deduplication
            filter_metadata={"user_id": user_id},
            score_threshold=settings.RAG_SIMILARITY_THRESHOLD,
        )

        if not raw_results:
            logger.debug("No memories found above threshold", query=query[:50])
            return []

        # 3. Rerank
        reranked = await self.reranker.rerank(query, raw_results, top_k=top_k * 2)

        # 4. Deduplicate
        deduplicated = self.deduplicator.deduplicate(reranked)

        # 5. Compress to token budget
        compressed = self.compressor.compress(deduplicated[:top_k])

        logger.info(
            "Memories retrieved",
            raw=len(raw_results),
            after_rerank=len(reranked),
            after_dedupe=len(deduplicated),
            final=len(compressed),
        )
        return compressed

    async def retrieve_hierarchical_context(
        self,
        query: str,
        user_id: str,
        top_k: int = settings.RAG_TOP_K,
    ) -> tuple[list[str], list[str]]:
        """
        Hierarchical retrieval pipeline:
        1. Retrieve relevant conversation summaries
        2. Retrieve relevant granular memories (embedded, reranked, deduplicated, compressed)
        3. Merge and rank by importance, similarity, and recency

        Returns (summaries_list, memories_list).
        """
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_text(query)

        # 1. Search conversation summaries
        summary_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=2,
            filter_metadata={"user_id": user_id, "is_summary": True},
            score_threshold=0.50,
        )
        summaries = [res.content for res in summary_results if res.content]

        # 2. Search detailed memories
        raw_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k * 3,
            filter_metadata={"user_id": user_id},
            score_threshold=settings.RAG_SIMILARITY_THRESHOLD,
        )

        # Filter out summary documents from granular memory list if any matched
        detailed_raw = [r for r in raw_results if not r.metadata.get("is_summary")]

        memories: list[str] = []
        if detailed_raw:
            reranked = await self.reranker.rerank(query, detailed_raw, top_k=top_k * 2)
            deduplicated = self.deduplicator.deduplicate(reranked)
            memories = self.compressor.compress(deduplicated[:top_k])

        return summaries, memories

    # ── BUILD PROMPT ──────────────────────────────────────────────────────────

    async def build_prompt(
        self,
        user_query: str,
        conversation_history: list[dict],
        user_id: str,
    ) -> tuple[list["ChatMessage"], int]:
        """
        Build the complete prompt with injected summaries and memories.
        Returns (messages, total_context_items_count).
        """
        summaries, memories = await self.retrieve_hierarchical_context(user_query, user_id)

        current_datetime = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        messages = self.prompt_builder.build(
            user_query=user_query,
            conversation_history=conversation_history,
            retrieved_memories=memories,
            current_datetime=current_datetime,
            summaries=summaries,
        )
        return messages, len(summaries) + len(memories)

    async def build_prompt_with_debug(
        self,
        user_query: str,
        conversation_history: list[dict],
        user_id: str,
        conversation_id: str = "",
    ) -> tuple[list["ChatMessage"], int, dict]:
        """
        Build prompt while capturing full RAG pipeline telemetry and explainability metadata.
        Returns (messages, total_context_items_count, debug_info_dict).
        """
        import time

        # Timing: Embedding
        t0 = time.perf_counter()
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_text(user_query)
        t_embed = (time.perf_counter() - t0) * 1000

        # Timing: Summary Retrieval
        t1 = time.perf_counter()
        summary_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=2,
            filter_metadata={"user_id": user_id, "is_summary": True},
            score_threshold=0.50,
        )
        t_summary = (time.perf_counter() - t1) * 1000

        summaries_list = []
        debug_summaries = []
        for s in summary_results:
            summaries_list.append(s.content)
            debug_summaries.append({
                "summary": s.content,
                "similarity_score": round(s.similarity_score, 4),
                "topics": s.metadata.get("topics", "[]"),
                "conversation_id": s.metadata.get("conversation_id", conversation_id),
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            })

        # Timing: Memory Retrieval & Ranking
        t2 = time.perf_counter()
        raw_results = await self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=settings.RAG_TOP_K * 3,
            filter_metadata={"user_id": user_id},
            score_threshold=settings.RAG_SIMILARITY_THRESHOLD,
        )
        detailed_raw = [r for r in raw_results if not r.metadata.get("is_summary")]

        memories_list = []
        debug_memories = []
        ranking_breakdown = []

        if detailed_raw:
            reranked = await self.reranker.rerank(user_query, detailed_raw, top_k=settings.RAG_TOP_K * 2)
            deduplicated = self.deduplicator.deduplicate(reranked)
            memories_list = self.compressor.compress(deduplicated[:settings.RAG_TOP_K])

            for idx, item in enumerate(detailed_raw[:settings.RAG_TOP_K]):
                sim = item.similarity_score
                imp = item.metadata.get("importance_score", 0.5)
                final_score = round(sim * 0.6 + imp * 0.4, 4)

                mem_info = {
                    "id": item.id,
                    "category": item.metadata.get("memory_type", "general"),
                    "memory": item.content,
                    "importance_score": imp,
                    "confidence_score": item.metadata.get("confidence", 0.85),
                    "similarity_score": round(sim, 4),
                    "final_score": final_score,
                    "version": item.metadata.get("version", 1),
                    "status": item.metadata.get("status", "ACTIVE"),
                    "tags": item.metadata.get("tags", "[]"),
                    "reason": f"High semantic similarity ({sim:.2f}) and importance ({imp:.2f})",
                }
                debug_memories.append(mem_info)
                ranking_breakdown.append({
                    "rank": idx + 1,
                    "memory_id": item.id,
                    "category": item.metadata.get("memory_type", "general"),
                    "content": item.content[:60] + "...",
                    "similarity_score": round(sim, 4),
                    "importance_score": imp,
                    "final_score": final_score,
                })

        t_memory = (time.perf_counter() - t2) * 1000

        current_datetime = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        messages = self.prompt_builder.build(
            user_query=user_query,
            conversation_history=conversation_history,
            retrieved_memories=memories_list,
            current_datetime=current_datetime,
            summaries=summaries_list,
        )

        full_prompt_text = "\n\n".join(
            f"[{msg.role.upper()}]:\n{msg.content}" for msg in messages
        )

        debug_info = {
            "query": user_query,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": len(query_embedding),
            "embedding_time_ms": round(t_embed, 2),
            "summary_retrieval_time_ms": round(t_summary, 2),
            "memory_retrieval_time_ms": round(t_memory, 2),
            "retrieved_summaries": debug_summaries,
            "retrieved_memories": debug_memories,
            "ranking_breakdown": ranking_breakdown,
            "final_prompt": full_prompt_text,
            "system_prompt": messages[0].content if messages else "",
            "messages_count": len(messages),
            "conversation_id": conversation_id,
            "total_summaries": len(debug_summaries),
            "total_memories": len(debug_memories),
            "prompt_token_length": len(full_prompt_text.split()),
        }

        return messages, len(summaries_list) + len(memories_list), debug_info
