"""Weaviate vector store — local self-hosted, 768-dim (Tier B: text-embedding-3-small:768)."""

import asyncio
import logging
import uuid as uuid_lib

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.vector_store.weaviate")

# Tier B dimension (text-embedding-3-small:768)
VECTOR_DIMENSION = 768


class WeaviateVectorStore:
    """Weaviate-backed vector store (local). Collection: self-provided vectors, dim 768."""

    def __init__(self):
        settings = get_settings()
        self._url = (settings.weaviate_url or "http://localhost:8080").rstrip("/")
        self._api_key = settings.weaviate_api_key
        self._class = settings.weaviate_class or "Embedding"
        self._client = None
        self._collection = None

    def _parse_url(self) -> tuple[str, int, int]:
        """Return (host, port, grpc_port) from WEAVIATE_URL."""
        # e.g. http://localhost:8080 or http://weaviate:8080
        rest = self._url.replace("https://", "").replace("http://", "").strip("/")
        parts = rest.split("/")[0].split(":")
        host = parts[0] or "localhost"
        port = int(parts[1]) if len(parts) > 1 else 8080
        grpc_port = 50051  # Weaviate default
        return host, port, grpc_port

    def _get_client(self):
        if self._client is None:
            try:
                import weaviate
                from weaviate.auth import AuthApiKey
            except ImportError:
                raise ImportError(
                    "Weaviate backend requires: pip install weaviate-client. "
                    "See docs/PINECONE_WEAVIATE_INTEGRATION.md"
                )
            host, port, grpc_port = self._parse_url()
            if self._api_key:
                # Cloud: use URL as cluster URL
                self._client = weaviate.connect_to_weaviate_cloud(
                    self._url,
                    auth_credentials=AuthApiKey(self._api_key),
                )
            else:
                # Local self-hosted
                self._client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                )
        return self._client

    def _ensure_collection(self):
        """Create collection if not exists: self-provided vectors (768 dim from first insert)."""
        client = self._get_client()
        if self._collection is not None:
            return
        try:
            from weaviate.classes.config import Configure, Property, DataType
            if client.collections.exists(self._class):
                self._collection = client.collections.get(self._class)
                return
            # Self-provided vectors (Tier B = 768 dim); Weaviate infers dim from first insert
            client.collections.create(
                name=self._class,
                vector_config=Configure.Vectors.self_provided(),
                properties=[
                    Property(name="object_type", data_type=DataType.TEXT),
                    Property(name="object_id", data_type=DataType.TEXT),
                    Property(name="model_id", data_type=DataType.TEXT),
                ],
            )
            self._collection = client.collections.get(self._class)
        except Exception as e:
            if client.collections.exists(self._class):
                self._collection = client.collections.get(self._class)
            else:
                logger.exception("Weaviate ensure_collection failed: %s", e)
                raise

    def _uuid(self, object_type: str, object_id: str, model_id: str) -> str:
        """Stable UUID for upsert idempotency."""
        raw = f"{object_type}:{object_id}:{model_id}"
        return str(uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, raw))

    def _upsert_sync(self, uid: str, props: dict, embedding: list[float]) -> None:
        """Sync upsert (run in thread)."""
        try:
            self._collection.data.insert(uuid=uid, properties=props, vector=embedding)
        except Exception as e:
            if "already exists" in str(e).lower() or "conflict" in str(e).lower():
                self._collection.data.replace(uuid=uid, properties=props, vector=embedding)
            else:
                raise

    async def upsert(
        self,
        object_type: str,
        object_id: str,
        model_id: str,
        embedding: list[float],
    ) -> None:
        if len(embedding) != VECTOR_DIMENSION:
            raise ValueError(f"Embedding dimension must be {VECTOR_DIMENSION}, got {len(embedding)}")
        self._ensure_collection()
        uid = self._uuid(object_type, object_id, model_id)
        props = {"object_type": object_type, "object_id": object_id, "model_id": model_id}
        await asyncio.to_thread(self._upsert_sync, uid, props, embedding)

    def _search_sync(self, vector: list[float], model_id: str, object_type: str, top_k: int):
        from weaviate.classes.query import Filter, MetadataQuery
        return self._collection.query.near_vector(
            near_vector=vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
            filters=(
                Filter.by_property("object_type").equal(object_type)
                & Filter.by_property("model_id").equal(model_id)
            ),
        )

    async def search(
        self,
        vector: list[float],
        model_id: str,
        object_type: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        self._ensure_collection()
        response = await asyncio.to_thread(
            self._search_sync, vector, model_id, object_type, top_k
        )
        out = []
        for obj in response.objects:
            oid = obj.properties.get("object_id", str(obj.uuid)) if obj.properties else str(obj.uuid)
            dist = obj.metadata.distance if obj.metadata and hasattr(obj.metadata, "distance") else 0.0
            score = float(1.0 - dist) if dist is not None else 0.9
            out.append((oid, score))
        return out

    def _get_cluster_vectors_sync(self, model_id: str, limit: int):
        from weaviate.classes.query import Filter
        return self._collection.query.fetch_objects(
            limit=limit,
            include_vector=True,
            filters=(
                Filter.by_property("object_type").equal("cluster")
                & Filter.by_property("model_id").equal(model_id)
            ),
        )

    async def get_cluster_vectors(
        self,
        model_id: str,
        limit: int = 500,
    ) -> list[tuple[str, list[float]]]:
        self._ensure_collection()
        response = await asyncio.to_thread(self._get_cluster_vectors_sync, model_id, limit)
        result = []
        for obj in response.objects:
            oid = obj.properties.get("object_id", "") if obj.properties else ""
            vec = obj.vector
            if isinstance(vec, dict):
                vec = vec.get("default", [])
            if vec is not None and not isinstance(vec, list):
                vec = list(vec)
            if oid and vec:
                result.append((oid, list(vec)))
        return result
