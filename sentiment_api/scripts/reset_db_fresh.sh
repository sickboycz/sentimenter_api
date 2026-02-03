#!/usr/bin/env bash
# sentiment_api — Reset DB to fresh install, then re-seed universes (sources, nasdaq, sectors, industries).
# Does NOT touch source_registry.yaml or registry CSVs; those stay as-is.
# Universe CSVs are read from registry/ or artifacts/ (artifacts/ is in git and used when registry has no CSVs).
#
# Usage (from sentiment_api/ with Postgres + API containers):
#   ./scripts/reset_db_fresh.sh
#
# Steps:
#   1. DROP SCHEMA public CASCADE; CREATE SCHEMA public
#   2. Apply all migrations (base + v1.1)
#   3. Seed universes (sectors, industries, S&P 500, Nasdaq-100) via refresh_universes (uses artifacts/ or registry/)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$COMPOSE_DIR/migrations"

cd "$COMPOSE_DIR"

if [[ -z "${COMPOSE_FILES:-}" ]]; then
  COMPOSE_FILES="-f docker-compose.yml"
  # Only add production overlay when production env exists (avoid "env file not found" in dev)
  if [[ -f docker-compose.production.yml ]] && [[ -f /etc/sentimenter/env ]]; then
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.production.yml"
  fi
fi

run_psql() {
  docker compose $COMPOSE_FILES exec -T postgres psql -U sentiment -d sentiment "$@"
}

echo "[*] Resetting DB to fresh install (keep sources/nasdaq/sectors in registry, re-seed from CSVs)..."

echo "[*] Dropping public schema and recreating..."
run_psql -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO sentiment; GRANT ALL ON SCHEMA public TO public;"

echo "[*] Applying migrations from zero..."
for f in \
  "$MIGRATIONS_DIR/00_base_schema.sql" \
  "$MIGRATIONS_DIR/v1.1_add_universes.sql" \
  "$MIGRATIONS_DIR/v1.1_add_industries.sql" \
  "$MIGRATIONS_DIR/v1.1_asset_targeting_audit.sql" \
  "$MIGRATIONS_DIR/v1.1_retention_tombstone.sql"; do
  if [[ -f "$f" ]]; then
    echo "[*] Applying $(basename "$f")..."
    run_psql -f - < "$f" || { echo "[!] Failed: $f"; exit 1; }
  else
    echo "[!] Missing: $f"; exit 1
  fi
done
# Default: 384 dim (base schema). For 768-dim run v1.2_embedding_dim_768.sql manually; then v1.3 to switch back to 384.
if [[ -f "$MIGRATIONS_DIR/v1.3_embedding_dim_384.sql" ]]; then
  echo "[*] Applying v1.3_embedding_dim_384.sql (embeddings 384)..."
  run_psql -f - < "$MIGRATIONS_DIR/v1.3_embedding_dim_384.sql" || { echo "[!] Failed: v1.3_embedding_dim_384.sql"; exit 1; }
fi

for f in v1.4_llm_call_cache.sql v1.4_asset_allocations.sql v1.4_forward_eval_asset.sql; do
  if [[ -f "$MIGRATIONS_DIR/$f" ]]; then
    echo "[*] Applying $f..."
    run_psql -f - < "$MIGRATIONS_DIR/$f" || { echo "[!] Failed: $f"; exit 1; }
  fi
done

echo "[*] Seeding universes (sectors, industries, S&P 500, Nasdaq-100)..."
docker compose $COMPOSE_FILES exec -T api python -c "
import asyncio
from sentiment_api.universe.refresh import refresh_universes
print(asyncio.run(refresh_universes()))
" || { echo "[!] Seed failed (is API container up and registry mounted?)"; exit 1; }

echo "[+] DB reset complete. Sources/registry unchanged; universes re-seeded."
