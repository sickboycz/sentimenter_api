"""L0 artifacts: save raw HTML and extracted text to object store."""

import logging
from pathlib import Path
from datetime import datetime

from sentiment_api.config import get_settings

logger = logging.getLogger("sentiment_api.ingest.artifacts")


def artifact_path(source_id: str, article_id: str, ext: str, root: Path | None = None) -> Path:
    """Path: {root}/news/{source_id}/{yyyy}/{mm}/{dd}/{article_id}.{ext}"""
    root = root or get_settings().artifact_root
    now = datetime.utcnow()
    p = root / "news" / source_id / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    return p / f"{article_id}.{ext}"


def save_artifact(content: str, path: Path) -> bool:
    """Save content to path. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.warning("Save artifact failed %s: %s", path, e)
        return False


def save_l0(article_id: str, source_id: str, html: str, text: str) -> tuple[str | None, str | None]:
    """Save L0 HTML and text. Returns (html_path, text_path) relative to artifact_root."""
    root = get_settings().artifact_root
    root.mkdir(parents=True, exist_ok=True)
    hp = artifact_path(source_id, article_id, "html", root)
    tp = artifact_path(source_id, article_id, "txt", root)
    ok_h = save_artifact(html, hp) if html else False
    ok_t = save_artifact(text, tp) if text else False
    rel = lambda p: str(p.relative_to(root)) if p.exists() else None
    return (rel(hp) if ok_h else None, rel(tp) if ok_t else None)
