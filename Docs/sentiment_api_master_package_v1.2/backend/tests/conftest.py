import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="session")
def client():
    # Provide a default API key for tests
    os.environ.setdefault("SENTIMENT_API_API_KEYS", "test_key_1234567890abcdef")
    return TestClient(app)

@pytest.fixture(scope="session")
def api_key():
    return "test_key_1234567890abcdef"
