"""Vector store abstraction for embeddings (pgvector, Pinecone, Weaviate)."""

from sentiment_api.vector_store.base import VectorStore
from sentiment_api.vector_store.pgvector import PgVectorStore

__all__ = ["VectorStore", "PgVectorStore", "get_vector_store"]


def get_vector_store(backend: str, conn=None):
    """Return the vector store implementation for the given backend."""
    if backend == "pgvector":
        return PgVectorStore(conn)
    if backend == "pinecone":
        from sentiment_api.vector_store.pinecone_client import PineconeVectorStore
        return PineconeVectorStore()
    if backend == "weaviate":
        from sentiment_api.vector_store.weaviate_client import WeaviateVectorStore
        return WeaviateVectorStore()
    raise ValueError(f"Unknown vector_store_backend: {backend}")
