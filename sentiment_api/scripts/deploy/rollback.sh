#!/usr/bin/env bash
# sentiment_api — rollback (Generic Service Manual §11.5)
#
# Usage: sudo ./rollback.sh

set -e

SERVICE=sentimenter
USER=$SERVICE
HOME_DIR="/srv/${SERVICE}"
REPO_DIR="${HOME_DIR}/repo"
COMPOSE_DIR="${REPO_DIR}/sentiment_api"
ENV_FILE="/etc/${SERVICE}/env"

echo "[*] sentiment_api rollback"

cd "$REPO_DIR" || { echo "[!] Repo not found"; exit 1; }

sudo -u "$USER" git reset --hard HEAD~1

cd "$COMPOSE_DIR" || exit 1

sudo -u "$USER" bash -c "
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml build --no-cache
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml up -d
"

systemctl restart sentimenter-docker 2>/dev/null || true

echo "[+] Rollback complete"
