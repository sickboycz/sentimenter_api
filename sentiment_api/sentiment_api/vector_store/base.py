"""Vector store protocol (abstraction for pgvector, Pinecone, Weaviate)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    """Interface for embedding storage and similarity search (all methods async)."""

    async def upsert(
        self,
        object_type: str,
        object_id: str,
        model_id: str,
        embedding: list[float],
    ) -> None:
        """Upsert one embedding. Id is derived from object_type, object_id, model_id."""
        ...

    async def search(
        self,
        vector: list[float],
        model_id: str,
        object_type: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Return (object_id, score) pairs by cosine similarity, most similar first."""
        ...

    async def get_cluster_vectors(
        self,
        model_id: str,
        limit: int = 500,
    ) -> list[tuple[str, list[float]]]:
        """Return (cluster_id, embedding) for clusters. Used by worker for find_nearest_cluster."""
        ...
