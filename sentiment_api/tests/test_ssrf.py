"""SSRF block: fetcher must reject private/reserved IPs."""

from sentiment_api.collectors.http_client import _block_ssrf_host


def test_private_ip_rejected():
    try:
        _block_ssrf_host("127.0.0.1")
        assert False, "Expected ValueError for 127.0.0.1"
    except ValueError as e:
        assert "SSRF" in str(e)


def test_localhost_rejected():
    try:
        _block_ssrf_host("localhost")
        assert False, "Expected ValueError for localhost"
    except ValueError as e:
        assert "SSRF" in str(e)


def test_private_10_rejected():
    try:
        _block_ssrf_host("10.0.0.1")
        assert False, "Expected ValueError for 10.0.0.1"
    except ValueError as e:
        assert "SSRF" in str(e)


def test_private_192_rejected():
    try:
        _block_ssrf_host("192.168.1.1")
        assert False, "Expected ValueError for 192.168.1.1"
    except ValueError as e:
        assert "SSRF" in str(e)


def test_public_allowed():
    # Should not raise (may raise if resolution fails in sandbox)
    try:
        _block_ssrf_host("api.gdeltproject.org")
    except ValueError as e:
        if "resolution" in str(e).lower():
            pass  # ok in sandbox without network
        else:
            raise
