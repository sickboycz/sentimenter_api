#!/usr/bin/env python3
"""
Check all RSS feed_urls in source_registry.yaml and report HTTP status (especially 403).
Usage: python scripts/check_feed_status.py [--registry PATH] [--timeout N]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPT_DIR.parent / "registry" / "source_registry.yaml"
TIMEOUT = 12.0
USER_AGENT = "Mozilla/5.0 (compatible; Sentimenter/1.0; +https://github.com/sentimenter)"


def parse_registry_sources(path: Path) -> list[tuple[str, str, str]]:
    """Return [(source_id, name, feed_url), ...] for each source with feed_url. Skips rss-bridge URLs."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    sources: list[tuple[str, str, str]] = []
    # Block per source: source_id, name, feed_url (may span multiple lines)
    block = re.split(r"\n(?=  - source_id:)", text)
    for blk in block:
        sid = re.search(r"source_id:\s*(\S+)", blk)
        name = re.search(r'name:\s*["\']?([^"\'\n]+)["\']?', blk)
        feed = re.search(r'feed_url:\s*["\']?([^\s"\'"\n]+)["\']?', blk)
        if not feed:
            continue
        url = feed.group(1).strip().strip('"\'')
        if "rss-bridge" in url:
            continue
        sid_val = sid.group(1).strip() if sid else "unknown"
        name_val = (name.group(1).strip().strip('"\'') if name else "")[:80]
        sources.append((sid_val, name_val, url))
    return sources


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Check registry feed URLs for HTTP status (e.g. 403)")
    p.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="Path to source_registry.yaml")
    p.add_argument("--timeout", type=float, default=TIMEOUT, help="Request timeout seconds")
    p.add_argument("--only-403", action="store_true", help="Only print sources that returned 403")
    args = p.parse_args()

    sources = parse_registry_sources(args.registry)
    if not sources:
        print("No feed_url sources found in registry.", file=sys.stderr)
        return 1

    bad: list[tuple[str, str, str, int, str]] = []  # (source_id, name, url, status, error)
    for source_id, name, url in sources:
        try:
            r = httpx.get(
                url,
                timeout=args.timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
            status = r.status_code
            if status == 403 or (not args.only_403 and status >= 400):
                bad.append((source_id, name, url, status, ""))
        except Exception as e:
            bad.append((source_id, name, url, -1, str(e)[:80]))

    if args.only_403:
        bad = [(sid, n, u, st, err) for sid, n, u, st, err in bad if st == 403]

    for source_id, name, url, status, err in bad:
        if status == -1:
            print(f"{source_id}\t{status}\t{err}\t{url[:70]}")
        else:
            print(f"{source_id}\t{status}\t{url[:70]}")

    if not bad:
        print("No 403 or errors (all OK).", file=sys.stderr)
        return 0
    print(f"\nTotal: {len(bad)} with 403 or error", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
