"""SQLite cache for Tier B embeddings: (model_id, text_hash) -> vector (float32 bytes)."""

import hashlib
import logging
import sqlite3
import struct
import time
from pathlib import Path

logger = logging.getLogger("sentiment_api.retrieval.embedding_cache")


def _normalize_text(text: str) -> str:
    """Normalize for hashing: strip, collapse whitespace."""
    return " ".join((text or "").strip().split())


def text_hash(text: str) -> str:
    """Stable SHA256 hash of normalized text."""
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def _vector_to_blob(vec: list[float]) -> bytes:
    """Serialize float list to float32 bytes."""
    return struct.pack(f"{len(vec)}f", *vec)


def _blob_to_vector(blob: bytes) -> list[float]:
    """Deserialize float32 bytes to list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


class EmbeddingCacheSqlite:
    """SQLite-backed cache for Tier B vectors. Deterministic, audit-grade."""

    def __init__(self, path: Path | str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._hit_count = 0
        self._miss_count = 0

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=True)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    model_id TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    dim INTEGER NOT NULL,
                    vector BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (model_id, text_hash)
                )
                """
            )
            self._conn.commit()
        return self._conn

    def get_cached_vector(self, model_id: str, text_hash_key: str) -> list[float] | None:
        """Return cached vector or None. Increments hit/miss counters."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT dim, vector FROM embedding_cache WHERE model_id = ? AND text_hash = ?",
            (model_id, text_hash_key),
        ).fetchone()
        if row is None:
            self._miss_count += 1
            return None
        self._hit_count += 1
        return _blob_to_vector(row[1])

    def put_cached_vector(
        self,
        model_id: str,
        text_hash_key: str,
        vector: list[float],
    ) -> None:
        """Store vector (float32 blob). Overwrites if exists."""
        conn = self._get_conn()
        blob = _vector_to_blob(vector)
        dim = len(vector)
        now = time.time()
        conn.execute(
            """
            INSERT INTO embedding_cache (model_id, text_hash, dim, vector, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (model_id, text_hash) DO UPDATE SET
                vector = excluded.vector,
                created_at = excluded.created_at
            """,
            (model_id, text_hash_key, dim, blob, now),
        )
        conn.commit()

    def get_stats(self) -> tuple[int, int]:
        """Return (hit_count, miss_count)."""
        return (self._hit_count, self._miss_count)

    def reset_stats(self) -> None:
        """Reset hit/miss counters (for tests)."""
        self._hit_count = 0
        self._miss_count = 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
