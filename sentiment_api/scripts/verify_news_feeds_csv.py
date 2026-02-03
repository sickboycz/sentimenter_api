#!/usr/bin/env python3
"""Verify RSS feeds from Docs/news_feeds_master.csv: fetch each, analyze, determine fallback.
Outputs verified sources suitable for source_registry.yaml (optional_media_rss pack).
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import httpx

# Repo root: sentiment_api/scripts -> sentiment_api -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO_ROOT / "Docs" / "news_feeds_master.csv"
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry" / "source_registry.yaml"

TIMEOUT = 15.0
USER_AGENT = "Sentimenter/1.0 (feed verification; +https://github.com/sentimenter)"

# Existing feed URLs and source_ids we already have (from registry)
EXISTING_FEED_URLS = {
    "https://www.federalreserve.gov/feeds/feeds.htm",
    "https://www.bls.gov/feed/",
    "https://www.ecb.europa.eu/home/html/rss.en.html",
    "https://www.consilium.europa.eu/en/about-site/rss/",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.dw.com/rdf/rss-en-all",
    "https://www.ft.com/world?format=rss",
}
EXISTING_SOURCE_IDS = {
    "gdelt_doc_v2", "us_fed_rss", "us_bls_rss", "us_bea_releases", "us_census_feeds",
    "us_treasurydirect_rss", "us_treasury_press", "ecb_rss", "eurostat_rss", "eu_commission_press",
    "eu_council_rss", "boe_rss", "bis_rss", "world_bank_news_api", "imf_press", "oecd_news",
    "un_ga_rss", "us_state_rss", "europarl_rss", "eia_rss", "iaea_rss", "crisisgroup_rss",
    "bbc_world_rss", "aljazeera_rss", "dw_rss", "ft_rss_world",
}


def slug_source_id(name: str, root_domain: str, row_id: str) -> str:
    """Produce a unique source_id: lowercase alphanumeric + underscores, 3-64 chars."""
    raw = (name or root_domain or f"feed_{row_id}").strip()
    raw = re.sub(r"\s+", " ", raw)
    # Take first 50 chars, replace non-alnum with underscore
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()[:50]).strip("_")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "_", (root_domain or f"feed_{row_id}").lower()).strip("_")
    slug = (slug or f"feed_{row_id}")[:64]
    return slug if len(slug) >= 3 else f"{slug}_rss"


def is_xml_response(content_type: str, body: bytes) -> bool:
    if not content_type:
        return body.lstrip()[:100].strip().startswith(b"<?xml") or b"<rss" in body[:2000] or b"<feed" in body[:2000]
    ct = content_type.split(";")[0].strip().lower()
    if "xml" in ct or "rss" in ct or "atom" in ct:
        return True
    if "html" in ct:
        return False
    return body.lstrip()[:100].strip().startswith(b"<?xml") or b"<rss" in body[:2000] or b"<feed" in body[:2000]


def check_feed(url: str) -> tuple[bool, str]:
    """Try to fetch URL. Return (ok, message)."""
    if not url or not url.strip().startswith("http"):
        return False, "invalid_url"
    try:
        r = httpx.get(
            url,
            timeout=TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    except Exception as e:
        return False, str(e)[:80]
    if r.status_code != 200:
        return False, f"status_{r.status_code}"
    if not is_xml_response(r.headers.get("content-type", ""), r.content):
        return False, "not_xml"
    return True, "ok"


def load_existing_from_registry() -> None:
    """Update EXISTING_* from registry YAML if present."""
    if not REGISTRY_PATH.exists():
        return
    text = REGISTRY_PATH.read_text()
    for m in re.finditer(r"source_id:\s*([a-z0-9_\-]+)", text):
        EXISTING_SOURCE_IDS.add(m.group(1).strip())
    for m in re.finditer(r"feed_url:\s*[\"']?([^\s\"'\n]+)", text):
        EXISTING_FEED_URLS.add(m.group(1).strip().strip('"\''))


def main() -> int:
    load_existing_from_registry()
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}", file=sys.stderr)
        return 1
    verified = []
    seen_ids: set[str] = set()
    with open(CSV_PATH, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    # Prefer: government, major_news, public_broadcaster, finance_press; credibility A+ or A
    preferred_types = {"government", "major_news", "public_broadcaster", "finance_press"}
    preferred_tiers = {"A+", "A"}
    candidates = [
        r for r in rows
        if (r.get("source_type") or "").strip() in preferred_types
        and (r.get("credibility_tier") or "").strip() in preferred_tiers
    ]
    # Cap total to avoid timeout (~60 feeds = ~90s at 1.5s each)
    to_check = candidates[:80]
    for i, row in enumerate(to_check):
        rss_url = (row.get("rss_url") or "").strip()
        if not rss_url or rss_url in EXISTING_FEED_URLS:
            continue
        name = (row.get("name") or "").strip() or "Unknown"
        homepage = (row.get("homepage") or "").strip()
        root_domain = (row.get("root_domain") or "").strip()
        row_id = row.get("id", str(i))
        source_id = slug_source_id(name, root_domain, row_id)
        if source_id in EXISTING_SOURCE_IDS or source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        ok, msg = check_feed(rss_url)
        fallback = homepage if (homepage and homepage.startswith("http")) else None
        if ok:
            verified.append({
                "source_id": source_id,
                "name": name[:120],
                "feed_url": rss_url,
                "fallback_page_url": fallback,
                "root_domain": root_domain,
                "source_type": row.get("source_type", ""),
                "credibility_tier": row.get("credibility_tier", ""),
                "status": "ok",
            })
            print(f"OK   {source_id[:40]:40} {rss_url[:50]}", flush=True)
        else:
            # Still add with fallback so daemon can try RSS then scrape
            if fallback:
                verified.append({
                    "source_id": source_id,
                    "name": name[:120],
                    "feed_url": rss_url,
                    "fallback_page_url": fallback,
                    "root_domain": root_domain,
                    "source_type": row.get("source_type", ""),
                    "credibility_tier": row.get("credibility_tier", ""),
                    "status": f"fallback ({msg})",
                })
                print(f"FALLBACK {source_id[:36]:36} {msg} -> {fallback[:40]}", flush=True)
    # Write verified list for registry ingestion
    out = REPO_ROOT / "sentiment_api" / "scripts" / "verified_feeds_output.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_id", "name", "feed_url", "fallback_page_url", "root_domain", "source_type", "credibility_tier", "status"])
        w.writeheader()
        w.writerows(verified)
    print(f"\nVerified: {len(verified)} written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
