#!/usr/bin/env bash
# sentiment_api — create systemd unit only (e.g. after install failed before step 7)
# Usage: sudo ./create-service.sh [--enable]
#   --enable  Run systemctl enable sentimenter-docker

set -e

SERVICE=sentimenter
UNIT_FILE="/etc/systemd/system/sentimenter-docker.service"
COMPOSE_DIR="/srv/sentimenter/repo/sentiment_api"
ENV_FILE="/etc/sentimenter/env"

DO_ENABLE=false
for arg in "$@"; do
  case "$arg" in
    --enable) DO_ENABLE=true ;;
  esac
done

echo "[*] Creating systemd unit: $UNIT_FILE"

if [[ ! -d "$COMPOSE_DIR" ]]; then
  echo "[!] Compose dir not found: $COMPOSE_DIR"
  echo "    Create it (e.g. clone repo to /srv/sentimenter/repo) then re-run."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[!] Env file not found: $ENV_FILE"
  echo "    Create it and set DATABASE_URL, REDIS_URL, etc. then re-run."
  exit 1
fi

mkdir -p "$(dirname "$UNIT_FILE")"
cat > "$UNIT_FILE" << 'UNIT'
[Unit]
Description=sentiment_api Docker Compose stack
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=sentimenter
WorkingDirectory=/srv/sentimenter/repo/sentiment_api
EnvironmentFile=/etc/sentimenter/env
ExecStart=/usr/bin/docker compose --env-file /etc/sentimenter/env -f docker-compose.yml -f docker-compose.production.yml up -d
ExecStop=/usr/bin/docker compose --env-file /etc/sentimenter/env -f docker-compose.yml -f docker-compose.production.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
echo "[+] Unit created and daemon-reloaded"

if $DO_ENABLE; then
  systemctl enable sentimenter-docker
  echo "[+] Enabled sentimenter-docker (start on boot)"
fi

echo ""
echo "[*] Next: sudo systemctl start sentimenter-docker   # or restart if already created"
echo "     Check: systemctl status sentimenter-docker"
