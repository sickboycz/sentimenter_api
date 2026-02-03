"""Pinecone vector store (stub — implement per docs/PINECONE_WEAVIATE_INTEGRATION.md)."""

from sentiment_api.config import get_settings


class PineconeVectorStore:
    """Pinecone-backed vector store. Requires PINECONE_API_KEY, PINECONE_INDEX, dimension 768 (Tier B), metric cosine."""

    def __init__(self):
        settings = get_settings()
        if not settings.pinecone_api_key:
            raise ValueError("Pinecone backend requires PINECONE_API_KEY")
        self._index_name = settings.pinecone_index
        self._api_key = settings.pinecone_api_key
        self._env = settings.pinecone_environment
        # Lazy init of Pinecone index (optional dep: pip install pinecone-client)
        self._index = None

    def _get_index(self):
        if self._index is None:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=self._api_key)
                self._index = pc.Index(self._index_name)
            except ImportError:
                raise ImportError(
                    "Pinecone backend requires: pip install pinecone-client. "
                    "See docs/PINECONE_WEAVIATE_INTEGRATION.md"
                )
        return self._index

    @staticmethod
    def _id(object_type: str, object_id: str, model_id: str) -> str:
        return f"{object_type}:{object_id}:{model_id}"

    async def upsert(
        self,
        object_type: str,
        object_id: str,
        model_id: str,
        embedding: list[float],
    ) -> None:
        idx = self._get_index()
        vid = self._id(object_type, object_id, model_id)
        idx.upsert(vectors=[{
            "id": vid,
            "values": embedding,
            "metadata": {"object_type": object_type, "object_id": object_id, "model_id": model_id},
        }])

    async def search(
        self,
        vector: list[float],
        model_id: str,
        object_type: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        idx = self._get_index()
        res = idx.query(
            vector=vector,
            top_k=top_k,
            filter={"object_type": {"$eq": object_type}, "model_id": {"$eq": model_id}},
            include_metadata=True,
        )
        out = []
        for m in (res.matches or []):
            oid = m.metadata.get("object_id", m.id) if m.metadata else m.id
            score = float(m.score or 0.0)
            out.append((oid, score))
        return out

    async def get_cluster_vectors(
        self,
        model_id: str,
        limit: int = 500,
    ) -> list[tuple[str, list[float]]]:
        # Pinecone list/fetch: list index and fetch vectors for object_type=cluster.
        # list() returns vector ids; fetch(ids) returns vectors. Filter by metadata requires a query per chunk or use list + fetch.
        idx = self._get_index()
        result = []
        # Pinecone serverless/list returns ids; then fetch. For "get all clusters" we list with prefix or filter.
        # Pinecone gRPC list() with filter might not be available in all plans. Fallback: query with a zero vector and high top_k to get many (not ideal).
        # Stub: return empty; worker falls back to pgvector if needed, or implement list+fetch.
        return result
