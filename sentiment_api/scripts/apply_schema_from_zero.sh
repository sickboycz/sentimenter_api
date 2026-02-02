#!/usr/bin/env bash
# sentiment_api — apply full schema from zero (base + v1.1 migrations)
# Usage:
#   With Docker Compose (from sentiment_api/):
#     ./scripts/apply_schema_from_zero.sh
#   Or: docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
#         psql -U sentiment -d sentiment -f - < migrations/00_base_schema.sql
#
# Order: 00_base_schema.sql → v1.1_add_universes.sql → v1.1_add_industries.sql → v1.1_asset_targeting_audit.sql → v1.1_retention_tombstone.sql
# Safe to re-run (IF NOT EXISTS / ON CONFLICT). Requires: postgres container running.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$COMPOSE_DIR/migrations"

cd "$COMPOSE_DIR"

# Detect compose files (default: base + production if present)
COMPOSE_FILES="-f docker-compose.yml"
[[ -f docker-compose.production.yml ]] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.production.yml"

run_psql() {
  docker compose $COMPOSE_FILES exec -T postgres psql -U sentiment -d sentiment "$@"
}

echo "[*] Applying schema from zero (base + v1.1 migrations)..."

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

echo "[+] Schema from zero applied successfully."
