"""M2 — Normalization + translation (English-first)."""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import langdetect

from sentiment_api.collectors.base import RawItem
from sentiment_api.registry.models import RegistryDefaults

logger = logging.getLogger("sentiment_api.ingest.normalize")


def canonical_url(url: str, base: str | None = None) -> str:
    """Canonicalize URL (strip fragments, sort params, lowercase domain)."""
    if base:
        url = urljoin(base, url)
    p = urlparse(url)
    netloc = p.netloc.lower()
    path = p.path.rstrip("/") or "/"
    query = "&".join(sorted(p.query.split("&"))) if p.query else ""
    return f"{p.scheme}://{netloc}{path}" + (f"?{query}" if query else "")


def detect_language(text: str) -> str:
    """Detect language code."""
    if not text or len(text.strip()) < 20:
        return "en"
    try:
        return langdetect.detect(text)
    except Exception:
        return "en"


def translate_to_english(text: str, lang: str, provider: Any = None) -> tuple[str, str, float]:
    """Translate to English. Returns (text_en, provider, confidence).
    Uses OpenAI when translate_to_en=True; never optional for non-English.
    """
    if not text:
        return "", "skip", 1.0
    if lang == "en":
        return text, "skip", 1.0
    from sentiment_api.llm.translation import translate_openai
    out = translate_openai(text, from_lang=lang, to_lang="en")
    if out:
        return out, "openai", 0.95
    return text, "failed", 0.2


def normalize_item(
    item: RawItem | dict,
    defaults: RegistryDefaults,
    translate: bool = True,
    translation_provider: Any = None,
) -> dict[str, Any]:
    """Normalize raw item to English-first structure (AC-M2.1, AC-M2.2, AC-M2.3)."""
    if isinstance(item, dict):
        def _dt(v):
            if v is None:
                return None
            if hasattr(v, "isoformat"):
                return v
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    return None
            return None
        item = RawItem(
            source_id=item["source_id"],
            source_type=item.get("source_type", "rss"),
            url=item["url"],
            published_at=_dt(item.get("published_at")),
            fetched_at=_dt(item.get("fetched_at")) or datetime.now(timezone.utc),
            title_raw=item.get("title_raw", ""),
            content_raw=item.get("content_raw", ""),
            content_html=item.get("content_html", ""),
            metadata=item.get("metadata", {}),
        )
    url = canonical_url(item.url)
    title = (item.title_raw or "").strip()[:2000]
    content = (item.content_raw or "").strip()[:50000]
    lang = detect_language(title + " " + content)
    title_en = title
    content_en = content
    status = "ok"
    provider = "skip"
    confidence = 1.0
    if translate and lang != "en" and defaults.translate_to_en:
        title_en, provider, confidence = translate_to_english(title, lang, translation_provider)
        content_en, _, c2 = translate_to_english(content, lang, translation_provider)
        confidence = min(confidence, c2)
        if provider == "failed":
            status = "failed"
            try:
                from sentiment_api.metrics import translation_failures_total
                translation_failures_total(item.source_id)
            except Exception as ex:
                logger.debug("Translation metrics update skipped: %s", ex)
    if not title_en and content_en:
        title_en = content_en[:200]
    if not title_en:
        title_en = url
    published = item.published_at
    if published and published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    content_hash = hashlib.sha256((title_en + content_en).encode()).hexdigest()[:64]
    fetched_at = item.fetched_at or datetime.now(timezone.utc)
    fetched_at = fetched_at.replace(tzinfo=timezone.utc) if getattr(fetched_at, "tzinfo", None) is None else fetched_at
    return {
        "source_id": item.source_id,
        "url": url,
        "canonical_url": url,
        "published_at": published,
        "fetched_at": fetched_at,
        "lang_original": lang,
        "title_raw": item.title_raw,
        "title_en": title_en,
        "content_en": content_en,
        "translation_status": status,
        "translation_provider": provider,
        "translation_confidence": confidence,
        "content_hash": content_hash,
        "metadata": item.metadata,
    }
