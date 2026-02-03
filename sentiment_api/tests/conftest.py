"""Pytest fixtures for sentiment_api (v1.2 contract tests)."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Load .env from project root so scripts/tests get DATABASE_URL, REDIS_URL, OPENAI_API_KEY, etc.
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass

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
