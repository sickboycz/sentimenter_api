#!/usr/bin/env bash
# sentiment_api — Run comprehensive test pack.
#
# Usage (from sentiment_api/):
#   ./scripts/run_tests.sh              # all tests (e2e skipped unless SENTIMENT_E2E=1)
#   ./scripts/run_tests.sh --fast      # unit + API validation + retrieval integration (no DB-dependent contract)
#   SENTIMENT_E2E=1 ./scripts/run_tests.sh   # include e2e (needs Postgres + Redis)
#
# For full pass (contract + invariants + topics): ensure Postgres is up and DATABASE_URL set.
# Exit: 0 if all pass, 1 otherwise.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PYTEST="${PYTEST:-uv run pytest}"
export SENTIMENT_API_API_KEYS="${SENTIMENT_API_API_KEYS:-test_key_1234567890abcdef,rate_limit_test_key_12345678901234}"

echo "=== sentiment_api test pack (root=$ROOT) ==="

if [[ "${1:-}" == "--fast" ]]; then
  echo "Fast pack: unit + API cluster/retrieval + retrieval integration + ssrf + openapi + health/status/metrics (no DB)."
  $PYTEST \
    tests/unit/ \
    tests/test_api_cluster_and_retrieval.py \
    tests/integration/test_advanced_search_pipeline.py \
    tests/test_ssrf.py \
    tests/test_openapi_refs.py \
    tests/test_contract_responses.py::test_health_contract \
    tests/test_contract_responses.py::test_status_contract \
    tests/test_topics_and_metrics.py::test_metrics_endpoint \
    -v --tb=short
else
  # E2E tests are skipped unless SENTIMENT_E2E=1 (see test_pipeline_e2e.py).
  $PYTEST tests/ -v --tb=short
fi

echo ""
echo "=== test pack finished ==="
