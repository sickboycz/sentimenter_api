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

# Sync universe CSVs from repo artifacts to volume (so containers can seed)
ARTIFACTS_SRC="${COMPOSE_DIR}/artifacts"
ARTIFACTS_VOL="${HOME_DIR}/volumes/artifacts"
if [[ -d "$ARTIFACTS_SRC" ]]; then
  for f in sp500.csv nasdaq100.csv sectors.csv industries.csv; do
    if [[ -f "$ARTIFACTS_SRC/$f" ]]; then
      cp "$ARTIFACTS_SRC/$f" "$ARTIFACTS_VOL/$f" 2>/dev/null || true
      chown "$USER:$USER" "$ARTIFACTS_VOL/$f" 2>/dev/null || true
      chmod 644 "$ARTIFACTS_VOL/$f" 2>/dev/null || true
    fi
  done
  chown "$USER:$USER" "$ARTIFACTS_VOL" 2>/dev/null || true
  chmod 755 "$ARTIFACTS_VOL" 2>/dev/null || true
fi

sudo -u "$USER" bash -c "
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml build --no-cache
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml up -d
"

systemctl restart sentimenter-docker 2>/dev/null || true

# Optional: run permission check (requires check-permissions.sh in repo)
SCRIPT_PARENT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -x "$SCRIPT_PARENT/check-permissions.sh" ]] && "$SCRIPT_PARENT/check-permissions.sh" 2>/dev/null || true

echo "[+] Update complete"
