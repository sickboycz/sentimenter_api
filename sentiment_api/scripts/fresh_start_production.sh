#!/usr/bin/env bash
# sentiment_api — Remove current Docker build, rebuild without debugging, migrate DB, seed. Fresh start.
# Does NOT use docker-compose.debug.yml (no DEBUG_ATTACH, no debugpy).
#
# Usage (from sentiment_api/):
#   ./scripts/fresh_start_production.sh                # fresh DB (drops volumes), no debug
#   ./scripts/fresh_start_production.sh --keep-data    # keep volumes, only rebuild + migrate
#   ./scripts/fresh_start_production.sh --production  # use docker-compose.production.yml (needs /etc/sentimenter/env on server)
#
# Steps:
#   1. docker compose down (--volumes for fresh unless --keep-data)
#   2. docker compose build --no-cache (no debug overlay)
#   3. docker compose up -d postgres redis
#   4. Wait for postgres
#   5. docker compose up -d api
#   6. Wait for api
#   7. Run reset_db_fresh.sh (drop schema, apply migrations, seed universes)
#   8. docker compose up -d (all services)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$COMPOSE_DIR"

COMPOSE_FILES="-f docker-compose.yml"
KEEP_DATA=false
for arg in "$@"; do
  [[ "$arg" = "--keep-data" ]] && KEEP_DATA=true
  if [[ "$arg" = "--production" ]]; then
    [[ -f docker-compose.production.yml ]] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.production.yml"
  fi
done

echo "[*] Fresh start (production, no debug)..."

echo "[*] Stopping and removing containers (no debug overlay)..."
if $KEEP_DATA; then
  docker compose $COMPOSE_FILES down --remove-orphans
else
  docker compose $COMPOSE_FILES down --remove-orphans --volumes
fi

echo "[*] Rebuilding images (no INSTALL_DEBUGPY)..."
docker compose $COMPOSE_FILES build --no-cache

echo "[*] Starting postgres and redis..."
docker compose $COMPOSE_FILES up -d postgres redis

echo "[*] Waiting for postgres..."
sleep 3
for i in 1 2 3 4 5 6 7 8 9 10; do
  if docker compose $COMPOSE_FILES exec -T postgres pg_isready -U sentiment 2>/dev/null; then
    break
  fi
  echo "    attempt $i/10..."
  sleep 3
done
docker compose $COMPOSE_FILES exec -T postgres pg_isready -U sentiment || { echo "[!] Postgres not ready"; exit 1; }

echo "[*] Starting api (needed for seed)..."
docker compose $COMPOSE_FILES up -d api

echo "[*] Waiting for api..."
sleep 8

echo "[*] Migrating DB and seeding universes..."
export COMPOSE_FILES
"$SCRIPT_DIR/reset_db_fresh.sh" || { echo "[!] reset_db_fresh failed"; exit 1; }

echo "[*] Starting all services..."
docker compose $COMPOSE_FILES up -d

echo "[+] Fresh start complete. No debug overlay; DB migrated and seeded."
echo "    Check: docker compose $COMPOSE_FILES ps"
echo "    API:   curl -s http://127.0.0.1:8080/v1/health | head"
