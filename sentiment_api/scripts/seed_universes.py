#!/usr/bin/env python3
"""Seed sectors and universes. Run after applying v1.1 schema.
Usage: uv run python scripts/seed_universes.py
Or: uv run sentiment-api refresh-universes
Env: DATABASE_URL, SOURCE_REGISTRY_PATH, etc. Loads .env from project root when available.
"""

import asyncio
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from sentiment_api.universe.refresh import refresh_universes


if __name__ == "__main__":
    msg = asyncio.run(refresh_universes())
    print(msg)
