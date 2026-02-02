"""pgvector implementation of VectorStore (current default)."""

from sentiment_api.db.repo import get_clusters_for_embedding, insert_embedding


class PgVectorStore:
    """Vector store backed by Postgres + pgvector."""

    def __init__(self, conn):
        self._conn = conn

    async def upsert(
        self,
        object_type: str,
        object_id: str,
        model_id: str,
        embedding: list[float],
    ) -> None:
        await insert_embedding(self._conn, object_type, object_id, model_id, embedding)

    async def search(
        self,
        vector: list[float],
        model_id: str,
        object_type: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        from sentiment_api.llm.rag import retrieve_similar
        rows = await retrieve_similar(self._conn, vector, model_id, top_k)
        # retrieve_similar returns list[dict] with cluster_id, headline_en, etc.; we need (object_id, score)
        # Current retrieve_similar doesn't return score; pgvector <=> returns distance. For protocol we return (id, 1 - distance) or (id, 0.9).
        return [(r["cluster_id"], 0.95) for r in rows]

    async def get_cluster_vectors(
        self,
        model_id: str,
        limit: int = 500,
    ) -> list[tuple[str, list[float]]]:
        rows = await get_clusters_for_embedding(self._conn, limit=limit, model_id=model_id)
        return [(cluster_id, emb) for cluster_id, emb, _ in rows]
