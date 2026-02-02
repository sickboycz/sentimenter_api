#!/usr/bin/env bash
# sentiment_api — verify repo after pull (required files + optional git status)
# Usage: ./verify-repo.sh [--pull]
#   --pull  Run git fetch + git pull before checking (as user sentimenter)

set -e

COMPOSE_DIR="/srv/sentimenter/repo/sentiment_api"
DO_PULL=false
for arg in "$@"; do
  case "$arg" in
    --pull) DO_PULL=true ;;
  esac
done

REPO_DIR="$(dirname "$COMPOSE_DIR")"

echo "[*] Verifying repo at $COMPOSE_DIR"

if $DO_PULL; then
  echo "[*] Fetching and pulling..."
  (cd "$REPO_DIR" && sudo -u sentimenter git fetch origin && sudo -u sentimenter git status && sudo -u sentimenter git pull)
fi

MISSING=0
for f in \
  registry/source_registry.yaml \
  docker-compose.yml \
  docker-compose.production.yml \
  migrations/v1.1_add_universes.sql \
  infra/prometheus/prometheus.yml \
  infra/loki/loki-config.yaml; do
  if [[ -f "$COMPOSE_DIR/$f" ]]; then
    echo "  OK  $f"
  else
    echo "  MISSING  $f"
    MISSING=$((MISSING + 1))
  fi
done

if [[ -d "$COMPOSE_DIR/infra/grafana/provisioning" ]]; then
  echo "  OK  infra/grafana/provisioning/"
else
  echo "  MISSING  infra/grafana/provisioning/"
  MISSING=$((MISSING + 1))
fi

if [[ $MISSING -eq 0 ]]; then
  echo "[+] All required files present"
  exit 0
else
  echo "[!] $MISSING required path(s) missing. Check UPDATE_SERVER_MANUAL Step 2.1."
  exit 1
fi
