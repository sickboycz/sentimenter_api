"""Unit tests: get_cluster_l3_summary (db/repo)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentiment_api.db.repo import get_cluster_l3_summary


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_returns_none_when_no_row():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    out = await get_cluster_l3_summary(conn, "clu_abc123")
    assert out is None
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_returns_none_when_content_empty():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"content": None})
    out = await get_cluster_l3_summary(conn, "clu_xyz")
    assert out is None


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_returns_dict_when_content_is_dict():
    content = {
        "what_changed_en": "Markets rallied.",
        "why_it_matters_en": "Inflation data.",
        "what_to_watch_en": "Fed meeting.",
        "summary_bullets_en": ["Bullet 1"],
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"content": content})
    out = await get_cluster_l3_summary(conn, "clu_abc123")
    assert out is not None
    assert out["what_changed_en"] == "Markets rallied."
    assert out["why_it_matters_en"] == "Inflation data."
    assert out["what_to_watch_en"] == "Fed meeting."
    assert out["summary_bullets_en"] == ["Bullet 1"]


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_parses_json_string():
    content = {"what_changed_en": "Done.", "why_it_matters_en": ""}
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"content": json.dumps(content)})
    out = await get_cluster_l3_summary(conn, "clu_xyz")
    assert out is not None
    assert out["what_changed_en"] == "Done."


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_returns_none_when_content_invalid_json():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"content": "not valid json {"})
    out = await get_cluster_l3_summary(conn, "clu_xyz")
    assert out is None


@pytest.mark.asyncio
async def test_get_cluster_l3_summary_returns_none_when_content_is_list():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"content": ["array", "not", "dict"]})
    out = await get_cluster_l3_summary(conn, "clu_xyz")
    assert out is None
