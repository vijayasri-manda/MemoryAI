"""
RAG retrieval evaluation script.
Measures precision, recall, and MRR for memory retrieval.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class EvalSample:
    query: str
    relevant_ids: list[str]   # ground-truth memory IDs that should be retrieved
    description: str


# Sample evaluation dataset
EVAL_SAMPLES = [
    EvalSample(
        query="What programming language does the user prefer?",
        relevant_ids=["mem_python_pref"],
        description="Python preference retrieval",
    ),
    EvalSample(
        query="What projects is the user currently working on?",
        relevant_ids=["mem_project_rag", "mem_project_fastapi"],
        description="Current projects retrieval",
    ),
    EvalSample(
        query="What are the user's career goals?",
        relevant_ids=["mem_goal_ml_engineer"],
        description="Career goals retrieval",
    ),
    EvalSample(
        query="What database does the user use?",
        relevant_ids=["mem_db_postgres", "mem_db_chroma"],
        description="Database preference retrieval",
    ),
]


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Precision@K: fraction of top-K retrieved that are relevant."""
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Recall@K: fraction of relevant items in top-K retrieved."""
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)


def mean_reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """MRR: reciprocal rank of the first relevant item."""
    for i, r in enumerate(retrieved):
        if r in relevant:
            return 1.0 / (i + 1)
    return 0.0


async def evaluate_retrieval(vector_store, embedding_service, user_id: str, k: int = 5):
    """
    Run evaluation against EVAL_SAMPLES.
    Returns aggregate metrics.
    """
    precision_scores = []
    recall_scores = []
    mrr_scores = []

    for sample in EVAL_SAMPLES:
        query_embedding = await embedding_service.embed_text(sample.query)
        results = await vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=k,
            filter_metadata={"user_id": user_id},
        )
        retrieved_ids = [r.id for r in results]

        p = precision_at_k(retrieved_ids, sample.relevant_ids, k)
        r = recall_at_k(retrieved_ids, sample.relevant_ids, k)
        mrr = mean_reciprocal_rank(retrieved_ids, sample.relevant_ids)

        precision_scores.append(p)
        recall_scores.append(r)
        mrr_scores.append(mrr)

        print(f"[{sample.description}]")
        print(f"  Query: {sample.query}")
        print(f"  Retrieved: {retrieved_ids[:k]}")
        print(f"  Relevant:  {sample.relevant_ids}")
        print(f"  P@{k}={p:.3f}  R@{k}={r:.3f}  MRR={mrr:.3f}")
        print()

    avg_precision = sum(precision_scores) / len(precision_scores)
    avg_recall = sum(recall_scores) / len(recall_scores)
    avg_mrr = sum(mrr_scores) / len(mrr_scores)

    print("=" * 50)
    print(f"Mean P@{k}: {avg_precision:.3f}")
    print(f"Mean R@{k}: {avg_recall:.3f}")
    print(f"Mean MRR:  {avg_mrr:.3f}")

    return {
        "precision_at_k": avg_precision,
        "recall_at_k": avg_recall,
        "mrr": avg_mrr,
        "k": k,
        "num_samples": len(EVAL_SAMPLES),
    }


if __name__ == "__main__":
    print("RAG Evaluation Script")
    print("Run this with: python -m tests.rag.evaluate_retrieval")
    print("Requires: initialized vector store with test data loaded.")
    print()
    print("Evaluation metrics computed:")
    print(f"  - Precision@K (K=5)")
    print(f"  - Recall@K (K=5)")
    print(f"  - Mean Reciprocal Rank (MRR)")
