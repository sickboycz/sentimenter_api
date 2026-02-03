#!/usr/bin/env bash
# Full E2E: backend (pytest e2e) + frontend (Playwright).
# Prerequisites: Python 3.11+, Postgres + Redis (e.g. docker compose up -d postgres redis).
# Optional: API + worker running for live ops data in frontend.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer uv run (Python 3.11+); fallback to python3 -m
RUN_PYTHON=""
if command -v uv &>/dev/null; then
  RUN_PYTHON="uv run python -m pytest"
elif command -v python3.11 &>/dev/null; then
  RUN_PYTHON="python3.11 -m pytest"
elif command -v python3 &>/dev/null && python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
  RUN_PYTHON="python3 -m pytest"
else
  echo "Need Python 3.11+ (or uv). Install: uv, or python3.11."
  exit 1
fi

echo "=== Full E2E: backend (pytest e2e) + frontend (Playwright) ==="

# Backend E2E (needs DATABASE_URL, REDIS_URL; set SENTIMENT_E2E=1)
echo "[1/2] Backend E2E (pytest e2e)..."
export SENTIMENT_E2E=1
export DATABASE_URL="${DATABASE_URL:-postgresql://sentiment:sentiment@localhost:5432/sentiment}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
$RUN_PYTHON tests/integration/test_pipeline_e2e.py -v --tb=short
echo "Backend E2E passed."

# Frontend E2E (Playwright starts dev server; baseURL localhost:3000)
echo "[2/2] Frontend E2E (Playwright)..."
mkdir -p frontend/test-artifacts/screenshots
cd frontend
npm run test:e2e
echo "Frontend E2E passed."

echo "=== Full E2E done ==="
