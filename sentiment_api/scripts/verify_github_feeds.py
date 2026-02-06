#!/usr/bin/env python3
"""
Verify RSS feeds from gist (stungeye), plenary/awesome-rss-feeds README, and joshuawalcher/rssfeeds.
Check each feed URL is live; output YAML entries for registry (optional_media_rss).
Usage: python scripts/verify_github_feeds.py [--gist-url URL] [--plenary-readme PATH] [--output PATH]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR.parent / "registry" / "source_registry.yaml"
TIMEOUT = 8.0
USER_AGENT = "Sentimenter/1.0 (feed verification; +https://github.com/sentimenter)"

EXISTING_FEED_URLS: set[str] = set()
EXISTING_SOURCE_IDS: set[str] = set()


def load_existing_from_registry() -> None:
    if not REGISTRY_PATH.exists():
        return
    text = REGISTRY_PATH.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"source_id:\s*([a-z0-9_\-]+)", text):
        EXISTING_SOURCE_IDS.add(m.group(1).strip())
    for m in re.finditer(r"feed_url:\s*[\"']?([^\s\"'\n]+)", text):
        u = m.group(1).strip().strip('"\'')
        EXISTING_FEED_URLS.add(u)


def normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u.startswith("http"):
        return ""
    return u.rstrip("/") or u


def is_xml_response(content_type: str, body: bytes) -> bool:
    if not content_type:
        return body.lstrip()[:200].startswith(b"<?xml") or b"<rss" in body[:3000] or b"<feed" in body[:3000]
    ct = content_type.split(";")[0].strip().lower()
    if "xml" in ct or "rss" in ct or "atom" in ct:
        return True
    if "html" in ct and b"<rss" not in body[:3000] and b"<feed" not in body[:3000]:
        return False
    return body.lstrip()[:200].startswith(b"<?xml") or b"<rss" in body[:3000] or b"<feed" in body[:3000]


def check_feed(url: str) -> tuple[bool, str]:
    if not url or not url.strip().startswith("http"):
        return False, "invalid_url"
    try:
        r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    except Exception as e:
        return False, str(e)[:60]
    if r.status_code != 200:
        return False, f"status_{r.status_code}"
    if not is_xml_response(r.headers.get("content-type", ""), r.content):
        return False, "not_xml"
    return True, "ok"


def slug_source_id(feed_url: str, name: str = "") -> str:
    """Derive a short source_id from URL and optional name."""
    try:
        parsed = urlparse(feed_url)
        netloc = (parsed.netloc or "").replace("www.", "").lower()
        path = (parsed.path or "").strip("/")[:40]
        path_slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_") if path else ""
        base = f"{netloc.split('.')[0]}_{path_slug}" if path_slug else netloc.replace(".", "_")
        base = re.sub(r"[^a-z0-9_]", "_", base).strip("_")[:48]
        if not base:
            base = "feed"
        base = base or "feed"
        return base if len(base) >= 3 else f"{base}_rss"
    except Exception:
        return "feed_ext"


def fetch_gist_feeds(gist_url: str) -> list[tuple[str, str, str]]:
    """Return list of (feed_url, page_url, name) from gist JSON."""
    out = []
    try:
        r = httpx.get(
            gist_url,
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Gist fetch failed: {e}", file=sys.stderr)
        return out
    if not isinstance(data, list):
        return out
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        rss = (item.get("rss") or "").strip()
        if not rss or not rss.startswith("http"):
            continue
        url = (item.get("url") or "").strip() or rss
        name = (urlparse(rss).netloc or f"feed_{i}").replace("www.", "")
        out.append((normalize_url(rss), url, name))
    return out


def parse_plenary_readme(content: str) -> list[tuple[str, str]]:
    """Extract (feed_url, source_name) from plenary README tables. Primary Feed Url is 2nd column."""
    out = []
    # Table row: | Source name | https://... | optional third column |
    for m in re.finditer(r"^\|\s*([^|]+)\s*\|\s*(https?://[^\s|]+)\s*\|", content, re.MULTILINE):
        name = m.group(1).strip()[:80]
        feed_url = normalize_url(m.group(2))
        if feed_url and name and "Primary Feed Url" not in name and "------" not in name:
            out.append((feed_url, name))
    return out


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Verify RSS from gist/plenary/joshuawalcher, output YAML")
    p.add_argument("--gist-url", default="https://gist.githubusercontent.com/stungeye/fe88fc810651174d0d180a95d79a8d97/raw/crypto_news.json")
    p.add_argument("--plenary-readme", type=Path, help="Path to plenary README.md (or fetch News.opml for URLs)")
    p.add_argument("--output", type=Path, help="Append YAML to this file (default: print)")
    p.add_argument("--max-check", type=int, default=120, help="Max feeds to verify (default 120)")
    p.add_argument("--skip-verify", action="store_true", help="Skip HTTP check (only dedupe and emit)")
    args = p.parse_args()

    load_existing_from_registry()

    candidates: list[tuple[str, str, str]] = []  # (feed_url, name_or_page, origin)

    # 1) Gist
    gist_feeds = fetch_gist_feeds(args.gist_url)
    for feed_url, page_url, name in gist_feeds:
        if feed_url and feed_url not in EXISTING_FEED_URLS:
            candidates.append((feed_url, name, "gist"))

    # 2) Plenary README
    if args.plenary_readme and args.plenary_readme.exists():
        content = args.plenary_readme.read_text(encoding="utf-8", errors="replace")
        for feed_url, name in parse_plenary_readme(content):
            if feed_url and feed_url not in EXISTING_FEED_URLS:
                # Avoid duplicate URL from gist
                if not any(c[0] == feed_url for c in candidates):
                    candidates.append((feed_url, name, "plenary"))

    # Dedupe by feed_url
    seen_urls: set[str] = set()
    unique: list[tuple[str, str, str]] = []
    for feed_url, name, origin in candidates:
        if feed_url in seen_urls or feed_url in EXISTING_FEED_URLS:
            continue
        seen_urls.add(feed_url)
        unique.append((feed_url, name, origin))

    # Limit to avoid long run
    to_check = unique[: args.max_check]
    verified: list[dict] = []
    used_ids: set[str] = set()

    for feed_url, name, origin in to_check:
        source_id = slug_source_id(feed_url, name)
        while source_id in EXISTING_SOURCE_IDS or source_id in used_ids:
            source_id = source_id[:44] + "_" + str(len(used_ids))
        used_ids.add(source_id)

        if args.skip_verify:
            ok, msg = True, "skip"
        else:
            ok, msg = check_feed(feed_url)
        if not ok:
            print(f"SKIP {source_id[:42]:42} {msg} {feed_url[:50]}", file=sys.stderr)
            continue
        print(f"OK   {source_id[:42]:42} {feed_url[:56]}", flush=True)
        fallback = name if name.startswith("http") else None
        verified.append({
            "source_id": source_id,
            "name": (name if not name.startswith("http") else urlparse(feed_url).netloc or "RSS")[:100],
            "feed_url": feed_url,
            "fallback_page_url": fallback,
            "origin": origin,
        })

    if not verified:
        print("No new live feeds to add.", file=sys.stderr)
        return 0

    yaml_lines = []
    for v in verified:
        name = (v["name"] or "").replace('"', "'")
        yaml_lines.append(f'''  - source_id: {v["source_id"]}
    name: "{name}"
    pack: optional_media_rss
    type: rss
    enabled: true
    feed_url: "{v["feed_url"]}"
''')
        if v.get("fallback_page_url"):
            yaml_lines.append(f'    fallback_page_url: "{v["fallback_page_url"]}"\n')
        yaml_lines.append("""    credibility_tier: reputable_media
    license_class: open
    regions: ["GLOBAL"]
    topics: ["economy", "markets", "politics"]
""")

    yaml_block = "\n".join(yaml_lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(yaml_block, encoding="utf-8")
        print(f"\nWrote {len(verified)} entries to {args.output}", file=sys.stderr)
    else:
        print("\n# --- Append below to registry sources ---\n")
        print(yaml_block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
