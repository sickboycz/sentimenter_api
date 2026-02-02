from __future__ import annotations

import os
from pathlib import Path

import psycopg2

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def _connect():
    # Uses DATABASE_URL env, but expects psycopg2 format:
    # postgresql://user:pass@host:port/dbname
    url = os.environ.get("DATABASE_URL") or os.environ.get("SENTIMENT_API_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL or SENTIMENT_API_DATABASE_URL env var required for migrations")
    # SQLAlchemy URLs may be passed; strip +psycopg2
    url = url.replace("postgresql+psycopg2://", "postgresql://")
    return psycopg2.connect(url)

def apply_all():
    files = sorted([p for p in MIGRATIONS_DIR.iterdir() if p.suffix == ".sql"])
    if not files:
        print("No migrations found.")
        return
    conn = _connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for f in files:
                sql = f.read_text(encoding="utf-8")
                print(f"Applying {f.name} ...")
                cur.execute(sql)
        print("Migrations applied.")
    finally:
        conn.close()

if __name__ == "__main__":
    apply_all()
