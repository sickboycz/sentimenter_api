#!/usr/bin/env bash
# sentiment_api — safe update (no data loss)
# Follows Generic Service Installation & Update Manual (v2)
#
# Usage: sudo ./update.sh

set -e

SERVICE=sentimenter
USER=$SERVICE
HOME_DIR="/srv/${SERVICE}"
REPO_DIR="${HOME_DIR}/repo"
COMPOSE_DIR="${REPO_DIR}/sentiment_api"
ENV_FILE="/etc/${SERVICE}/env"

echo "[*] sentiment_api update"

cd "$REPO_DIR" || { echo "[!] Repo not found: $REPO_DIR"; exit 1; }

sudo -u "$USER" git fetch --all
sudo -u "$USER" git pull

cd "$COMPOSE_DIR" || { echo "[!] Compose dir not found"; exit 1; }

sudo -u "$USER" bash -c "
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml build --no-cache
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml up -d
"

systemctl restart sentimenter-docker 2>/dev/null || true

echo "[+] Update complete"
