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
for q in sentiment_api:ingest sentiment_api:normalize sentiment_api:summarize sentiment_api:score sentiment_api:index; do
  len=$("${COMPOSE_CMD[@]}" exec -T redis redis-cli LLEN "$q" 2>/dev/null || echo "?")
  echo "  $q: $len"
done
echo ""

# --- Registry (API container) ---
echo "--- Registry (API) ---"
reg_out=$("${COMPOSE_CMD[@]}" exec -T api sh -c 'test -r /etc/sentiment_api/source_registry.yaml && wc -l < /etc/sentiment_api/source_registry.yaml && grep -c "source_id:" /etc/sentiment_api/source_registry.yaml || true' 2>/dev/null)
if [[ -n "$reg_out" ]]; then
  lines=$(echo "$reg_out" | head -1)
  sources=$(echo "$reg_out" | tail -1)
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

# --- Worker logs (file, not stdout until next deploy) ---
echo "--- Worker logs (from file in container) ---"
echo "  Run: docker exec \$(docker ps -q -f name=worker) tail -200 /data/logs/worker.log"
echo "  Or:  docker exec \$(docker ps -q -f name=worker) grep -E 'Clustering DB error|Worker error|DB connection OK|Summarize:|Ingest:' /data/logs/worker.log | tail -50"
echo ""

# --- Zero clusters? ---
echo "--- Zero clusters? ---"
echo "  If articles > 0, clusters = 0, summarize queue = 0: run backfill_summarize to queue existing articles:"
echo "  docker compose exec api python /app/scripts/backfill_summarize.py"
echo "  Or: docker compose exec api python /app/scripts/backfill_summarize.py --dry-run"
echo ""

echo "=== end diagnostics ==="
