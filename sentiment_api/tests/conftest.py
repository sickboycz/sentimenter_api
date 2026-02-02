"""Pytest fixtures for sentiment_api (v1.2 contract tests)."""
import os
import pytest
from fastapi.testclient import TestClient

# Use env API keys for tests (bypasses DB)
os.environ.setdefault(
    "SENTIMENT_API_API_KEYS",
    "test_key_1234567890abcdef,rate_limit_test_key_12345678901234"
)


@pytest.fixture(scope="session")
def client():
    from sentiment_api.api.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def api_key():
    return "test_key_1234567890abcdef"
