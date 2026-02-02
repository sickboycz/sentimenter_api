"""RAG: vector retrieval + answer generation with citations."""

import json
import logging
import os
from typing import Any

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.llm.rag")


async def retrieve_similar(
    conn,
    query_embedding: list[float],
    model_id: str,
    top_k: int = 10,
) -> list[dict]:
    """Retrieve top K clusters by cosine similarity (pgvector <=> operator)."""
    vec_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
    rows = await conn.fetch(
        """
        SELECT e.object_id as cluster_id, c.headline_en, c.topics, c.impact
        FROM embeddings e
        JOIN clusters c ON c.cluster_id = e.object_id
        WHERE e.object_type = 'cluster' AND e.model = $1
        ORDER BY e.embedding <=> $2::vector
        LIMIT $3
        """,
        model_id,
        vec_str,
        top_k,
    )
    return [
        {
            "cluster_id": r["cluster_id"],
            "headline_en": r["headline_en"],
            "topics": list(r["topics"] or []),
            "impact": r["impact"] or {},
        }
        for r in rows
    ]


def generate_answer(query: str, contexts: list[dict]) -> tuple[str, list[dict]]:
    """Generate answer from contexts using LLM (GPT-5.2 escalation). Returns (answer, citations)."""
    from sentiment_api.llm.client import call_chat
    if not os.environ.get("OPENAI_API_KEY"):
        return "RAG requires OPENAI_API_KEY. Retrieved clusters but could not generate answer.", [
            {"cluster_id": c["cluster_id"], "headline_en": c["headline_en"], "relevance_score": 0.9}
            for c in contexts[:5]
        ]
    ctx_text = "\n".join(f"- [{c['cluster_id']}] {c['headline_en']}" for c in contexts[:10])
    answer = call_chat(
        "Answer the user's question based ONLY on the provided news cluster headlines. Cite cluster IDs. If the context doesn't contain relevant info, say so.",
        f"Context:\n{ctx_text}\n\nQuestion: {query}\n\nAnswer with citations:",
        temperature=0.2,
    )
    citations = [
        {"cluster_id": c["cluster_id"], "headline_en": c["headline_en"], "relevance_score": 0.95 - i * 0.05}
        for i, c in enumerate(contexts[:10])
    ]
    if not answer:
        answer = "Could not generate answer."
    return answer, citations
