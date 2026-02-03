#!/usr/bin/env bash
# sentiment_api — pipeline diagnostics (DB counts, queues, registry, embeddings schema)
# Run from sentiment_api/: ./scripts/diagnose-pipeline.sh
# Or with compose files: ./scripts/diagnose-pipeline.sh -f docker-compose.yml -f docker-compose.production.yml
#
# Usage: ./diagnose-pipeline.sh [COMPOSE_ARGS...]
#   COMPOSE_ARGS: e.g. -f docker-compose.yml -f docker-compose.production.yml (default: -f docker-compose.yml)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

COMPOSE_OPTS=(-f docker-compose.yml)
for arg in "$@"; do
  COMPOSE_OPTS+=("$arg")
done

COMPOSE_CMD=(docker compose "${COMPOSE_OPTS[@]}")

echo "=== sentiment_api pipeline diagnostics ==="
echo "  (from $ROOT)"
echo ""

# --- Postgres: counts ---
echo "--- Postgres counts ---"
for tbl in articles clusters events summaries runs embeddings; do
  count=$("${COMPOSE_CMD[@]}" exec -T postgres psql -U sentiment -d sentiment -t -A -c "SELECT COUNT(*) FROM $tbl;" 2>/dev/null) || count="?"
  echo "  $tbl: $count"
done
echo ""

# --- Redis: queue lengths ---
echo "--- Redis queue lengths ---"
for q in ingest normalize summarize score index; do
  len=$("${COMPOSE_CMD[@]}" exec -T redis redis-cli LLEN "sentiment_api:queue:$q" 2>/dev/null || echo "?")
  echo "  $q: $len"
done
echo ""

# --- Registry (API container) ---
echo "--- Registry (API) ---"
if "${COMPOSE_CMD[@]}" exec -T api test -r /etc/sentiment_api/source_registry.yaml 2>/dev/null; then
  lines=$("${COMPOSE_CMD[@]}" exec -T api wc -l < /etc/sentiment_api/source_registry.yaml 2>/dev/null || echo "0")
  sources=$("${COMPOSE_CMD[@]}" exec -T api grep -c "source_id:" /etc/sentiment_api/source_registry.yaml 2>/dev/null || echo "0")
  echo "  file: present ($lines lines, ~$sources source_id entries)"
else
  echo "  file: missing or unreadable"
fi
echo ""

# --- Embeddings table schema (pgvector) ---
echo "--- Embeddings table (pgvector) ---"
"${COMPOSE_CMD[@]}" exec -T postgres psql -U sentiment -d sentiment -c "
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'embeddings'
  ORDER BY ordinal_position;
" 2>/dev/null || echo "  (table or postgres unreachable)"
echo ""

# --- Worker last job (Redis) ---
echo "--- Worker last job (Redis) ---"
"${COMPOSE_CMD[@]}" exec -T redis redis-cli HGETALL sentiment_api:ops:worker_last_job 2>/dev/null || echo "  (redis unreachable)"
echo ""

echo "=== end diagnostics ==="
