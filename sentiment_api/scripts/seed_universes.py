#!/usr/bin/env python3
"""Seed sectors and universes. Run after applying v1.1 schema.
Usage: uv run python scripts/seed_universes.py
Or: uv run sentiment-api refresh-universes
"""

import asyncio

from sentiment_api.universe.refresh import refresh_universes


if __name__ == "__main__":
    msg = asyncio.run(refresh_universes())
    print(msg)
