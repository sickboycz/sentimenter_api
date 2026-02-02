#!/usr/bin/env bash
# sentiment_api — run validation checks
# Usage: ./run.sh [--skip-docker]
# Exit 0 = all pass, non-zero = failure

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FAILED=0
SKIP_DOCKER=false
for arg in "$@"; do
  case "$arg" in
    --skip-docker) SKIP_DOCKER=true ;;
  esac
done

echo "=== sentiment_api validation ==="

# 1. Pytest
echo ""
echo "[1/5] Pytest (unit + contract)..."
if uv run pytest tests/ -v --ignore=tests/test_sse_stream.py -q 2>/dev/null; then
  echo "  OK"
else
  echo "  FAIL"
  FAILED=1
fi

# 2. OpenAPI schema
echo ""
echo "[2/5] OpenAPI schema..."
if [[ -f openapi/sentiment_api.openapi.v1.2.yaml ]]; then
  echo "  OK openapi/sentiment_api.openapi.v1.2.yaml"
else
  echo "  FAIL schema missing"
  FAILED=1
fi

# 3. Required dirs/files
echo ""
echo "[3/5] Required files..."
MISSING=0
for f in schemas/defs.json infra/prometheus/prometheus.yml infra/grafana/provisioning/datasources/datasources.yml docker-compose.yml docker-compose.production.yml; do
  if [[ -f "$f" ]] || [[ -d "$f" ]]; then
    echo "  OK $f"
  else
    echo "  MISSING $f"
    MISSING=1
  fi
done
[[ $MISSING -eq 1 ]] && FAILED=1

# 4. Docker Compose config
echo ""
echo "[4/5] Docker Compose config..."
if docker compose -f docker-compose.yml config -q 2>/dev/null; then
  echo "  OK docker-compose.yml"
else
  echo "  FAIL docker-compose.yml"
  FAILED=1
fi

if ! $SKIP_DOCKER; then
  if docker compose -f docker-compose.yml -f docker-compose.production.yml config -q 2>/dev/null; then
    echo "  OK docker-compose.production.yml"
  else
    echo "  FAIL docker-compose.production.yml"
    FAILED=1
  fi
fi

# 5. Deployment scripts
echo ""
echo "[5/5] Deployment scripts..."
for f in scripts/deploy/install.sh scripts/deploy/update.sh scripts/deploy/rollback.sh; do
  if [[ -f "$f" ]] && [[ -x "$f" ]]; then
    echo "  OK $f"
  else
    echo "  MISSING/not exec $f"
    FAILED=1
  fi
done

echo ""
if [[ $FAILED -eq 0 ]]; then
  echo "=== All validation checks passed ==="
  exit 0
else
  echo "=== Some checks failed ==="
  exit 1
fi
