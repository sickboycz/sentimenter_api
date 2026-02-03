#!/usr/bin/env bash
# Start the stack with worker count and other vars from .env.
# Usage: from sentiment_api/ run: ./scripts/up-with-scale.sh
# Or: bash scripts/up-with-scale.sh
set -e
cd "$(dirname "$0")/.."
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi
WORKER_REPLICAS=${WORKER_REPLICAS:-6}
export WORKER_REPLICAS
echo "Starting stack with worker scale=${WORKER_REPLICAS} (from .env WORKER_REPLICAS, default 6)."
docker compose up -d --scale worker="${WORKER_REPLICAS}"
