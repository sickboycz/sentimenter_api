#!/usr/bin/env bash
# sentiment_api — fix everything: git, pull, rebuild, restart, then diagnose
#
# Usage:
#   Dev (from sentiment_api/):
#     ./scripts/fix-everything.sh
#     ./scripts/fix-everything.sh --pull --rebuild --restart
#   Production (on server, run as root or with sudo):
#     sudo ./scripts/fix-everything.sh --production --fix-git --pull --rebuild --restart
#
# Options:
#   --production     Use /srv/sentimenter/repo, sentimenter user, /etc/sentimenter/env
#   --fix-git        Add repo to git safe.directory (fixes "dubious ownership")
#   --pull           git fetch + pull
#   --rebuild        docker compose build --no-cache (all services)
#   --rebuild-worker Only rebuild worker image (faster; use after code changes to worker)
#   --restart        docker compose up -d; in production also restart sentimenter-docker
#   --diagnose       Run pipeline diagnostics (default: run at end if containers up)
#   --no-diagnose    Skip diagnostics at the end
#
# Without options: only runs diagnostics (and --fix-git if --production and git fails).

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
PRODUCTION=false
FIX_GIT=false
DO_PULL=false
DO_REBUILD=false
REBUILD_WORKER_ONLY=false
DO_RESTART=false
RUN_DIAGNOSE=true

# Production paths (align with deploy/install.sh and deploy/update.sh)
SERVICE=sentimenter
USER=$SERVICE
REPO_DIR="/srv/${SERVICE}/repo"
COMPOSE_DIR="${REPO_DIR}/sentiment_api"
ENV_FILE="/etc/${SERVICE}/env"

for arg in "$@"; do
  case "$arg" in
    --production)      PRODUCTION=true ;;
    --fix-git)         FIX_GIT=true ;;
    --pull)            DO_PULL=true ;;
    --rebuild)         DO_REBUILD=true ;;
    --rebuild-worker)  REBUILD_WORKER_ONLY=true ;;
    --restart)         DO_RESTART=true ;;
    --diagnose)        RUN_DIAGNOSE=true ;;
    --no-diagnose)     RUN_DIAGNOSE=false ;;
    -h|--help)
      head -30 "$0" | sed -n '2,/^$/p'
      exit 0
      ;;
  esac
done

# Compose command and working directory
if $PRODUCTION; then
  cd "$REPO_DIR" || { echo "[!] Repo not found: $REPO_DIR (run with --production on server)"; exit 1; }
  COMPOSE_OPTS=(--env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.production.yml)
  RUN_AS="sudo -u $USER"
  COMPOSE_CMD=("$RUN_AS" docker compose "${COMPOSE_OPTS[@]}")
  cd "$COMPOSE_DIR" || { echo "[!] Compose dir not found: $COMPOSE_DIR"; exit 1; }
else
  cd "$ROOT" || exit 1
  COMPOSE_OPTS=(-f docker-compose.yml)
  COMPOSE_CMD=(docker compose "${COMPOSE_OPTS[@]}")
fi

echo "=== sentiment_api fix-everything ==="
echo "  dir: $(pwd)"
echo "  production: $PRODUCTION"
echo ""

# --- Fix git safe.directory (server: dubious ownership) ---
if $FIX_GIT; then
  REPO_FOR_GIT="$REPO_DIR"
  $PRODUCTION || REPO_FOR_GIT="$ROOT"
  if [[ -d "$REPO_FOR_GIT/.git" ]]; then
    echo "[*] Adding safe.directory for $REPO_FOR_GIT"
    git config --global --add safe.directory "$REPO_FOR_GIT" 2>/dev/null || true
    echo "[+] Git safe.directory set"
  fi
  echo ""
fi

# --- Git pull ---
if $DO_PULL; then
  echo "[*] Git fetch and pull"
  if $PRODUCTION; then
    $RUN_AS git -C "$REPO_DIR" fetch --all
    $RUN_AS git -C "$REPO_DIR" pull
  else
    git -C "$ROOT" fetch --all 2>/dev/null || true
    git -C "$ROOT" pull
  fi
  echo "[+] Pull done"
  echo ""
fi

# --- Rebuild ---
if $DO_REBUILD || $REBUILD_WORKER_ONLY; then
  echo "[*] Docker build --no-cache"
  if $REBUILD_WORKER_ONLY; then
    "${COMPOSE_CMD[@]}" build --no-cache worker
  else
    "${COMPOSE_CMD[@]}" build --no-cache
  fi
  echo "[+] Build done"
  echo ""
fi

# --- Restart ---
if $DO_RESTART; then
  echo "[*] Docker compose up -d"
  "${COMPOSE_CMD[@]}" up -d
  if $PRODUCTION; then
    systemctl restart sentimenter-docker 2>/dev/null || true
  fi
  echo "[+] Stack restarted"
  echo "[*] Waiting for Postgres..."
  for i in {1..30}; do
    if "${COMPOSE_CMD[@]}" exec -T postgres pg_isready -U sentiment 2>/dev/null; then
      echo "[+] Postgres ready"
      break
    fi
    [[ $i -eq 30 ]] && echo "[!] Postgres not ready after 30s"
    sleep 2
  done
  echo ""
fi

# --- Diagnostics ---
if $RUN_DIAGNOSE; then
  echo "[*] Running pipeline diagnostics..."
  if $PRODUCTION; then
    $RUN_AS "$COMPOSE_DIR/scripts/diagnose-pipeline.sh" -f docker-compose.yml -f docker-compose.production.yml
  else
    "$SCRIPT_DIR/diagnose-pipeline.sh" "${COMPOSE_OPTS[@]}"
  fi
  echo ""
fi

# --- Worker log hint ---
echo "--- Worker logs ---"
echo "  Compose: ${COMPOSE_CMD[*]} logs worker --tail 200"
echo "  Or file: docker exec \$(docker ps -q -f name=worker) tail -200 /data/logs/worker.log"
echo ""
echo "=== fix-everything done ==="
