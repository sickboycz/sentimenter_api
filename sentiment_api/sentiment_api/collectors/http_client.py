"""Shared HTTP client with retries, backoff, robots.txt, SSRF block (AC-M1.3, 14.4, test matrix)."""

import ipaddress
import logging
import socket
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger("sentiment_api.collectors.http")


def _is_private_or_reserved(ip: str) -> bool:
    """True if IP is private/reserved (SSRF block)."""
    try:
        a = ipaddress.ip_address(ip)
        return (
            a.is_private
            or a.is_loopback
            or a.is_link_local
            or a.is_reserved
            or a.is_multicast
        )
    except ValueError:
        return True


def _block_ssrf_host(host: str) -> None:
    """Raise ValueError if host is private/reserved or resolves to such (SSRF block)."""
    if not host or host.startswith("."):
        raise ValueError("SSRF: invalid host")
    host_lower = host.lower().strip()
    if host_lower in ("localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"):
        raise ValueError("SSRF: localhost not allowed")
    if host_lower == "::1":
        raise ValueError("SSRF: loopback not allowed")
    # Host as IP literal
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError(f"SSRF: private/reserved IP not allowed: {host}")
        return
    except ValueError as e:
        if "SSRF:" in str(e):
            raise
    # Not an IP; resolve hostname
    # Resolve hostname
    try:
        addrinfos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"SSRF: host resolution failed: {exc}") from exc
    for _, _, _, _, sockaddr in addrinfos:
        ip = sockaddr[0] if isinstance(sockaddr, (list, tuple)) else sockaddr
        if _is_private_or_reserved(ip):
            raise ValueError(f"SSRF: private/reserved IP not allowed: {ip}")

# Retry config
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0


_robots_cache: dict[str, tuple[RobotFileParser, float]] = {}
_ROBOTS_CACHE_TTL = 3600
# Polite, identifiable User-Agent; format matches common crawler conventions to reduce 403 blocks
_DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; SentimentAPI/1.2; research data aggregation; +https://github.com/sickboycz/sentimenter_api)"


def _get_user_agent() -> str:
    import os
    return os.environ.get("SENTIMENT_API_USER_AGENT") or os.environ.get("USER_AGENT") or _DEFAULT_USER_AGENT


def _check_robots(url: str) -> bool:
    """Return True if fetch allowed by robots.txt."""
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or ""
    robots_url = f"{scheme}://{netloc}/robots.txt"
    now = time.time()
    if robots_url in _robots_cache:
        rp, ts = _robots_cache[robots_url]
        if now - ts < _ROBOTS_CACHE_TTL:
            return rp.can_fetch(_get_user_agent(), url)
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        with httpx.Client(timeout=5.0, headers={"User-Agent": _get_user_agent()}) as c:
            resp = c.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
        _robots_cache[robots_url] = (rp, now)
        return rp.can_fetch(_get_user_agent(), url)
    except Exception:
        return True  # allow on parse error


def fetch_with_retry(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    timeout: float = 20.0,
    follow_redirects: bool = True,
    respect_robots: bool = True,
    block_ssrf: bool = True,
) -> httpx.Response:
    """Fetch URL with retries and exponential backoff on 429/5xx (AC-M1.3). SSRF block by default."""
    parsed = urlparse(url)
    host = parsed.hostname
    if host and block_ssrf:
        _block_ssrf_host(host)
    if respect_robots and not _check_robots(url):
        raise PermissionError("robots.txt disallows this URL")
    last_exc: Exception | None = None
    backoff = INITIAL_BACKOFF
    headers = {"User-Agent": _get_user_agent()}
    with httpx.Client(timeout=timeout, follow_redirects=follow_redirects, headers=headers) as client:
        for attempt in range(MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    resp = client.get(url, params=params or {})
                else:
                    resp = client.request(method, url, params=params or {})
                if resp.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "HTTP %s from %s (attempt %d/%d), backing off %.1fs",
                        resp.status_code, url[:80], attempt + 1, MAX_RETRIES, backoff,
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in RETRY_STATUS_CODES or attempt >= MAX_RETRIES - 1:
                    raise
                last_exc = e
                logger.warning("HTTP %s (attempt %d/%d), backing off %.1fs", e.response.status_code, attempt + 1, MAX_RETRIES, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
            except (httpx.HTTPError, OSError) as e:
                last_exc = e
                if attempt >= MAX_RETRIES - 1:
                    raise
                logger.warning("Fetch failed %s (attempt %d/%d): %s, backing off %.1fs", url[:80], attempt + 1, MAX_RETRIES, e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
    if last_exc:
        raise last_exc
    raise RuntimeError("fetch_with_retry exhausted")
