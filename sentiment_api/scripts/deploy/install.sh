#!/usr/bin/env bash
# sentiment_api — production deployment script
# Follows Generic Service Installation & Update Manual (v2)
# User: sentimenter | Data: /srv/sentimenter/volumes/ (out-of-Docker)
#
# Usage: sudo ./install.sh [--skip-user] [--skip-repo] [--service-only]
#   --skip-user     Do not create user/dirs (already present)
#   --skip-repo     Do not clone repo (already present)
#   --service-only  Only create systemd unit (e.g. after install failed before step 7)

set -e

SERVICE=sentimenter
USER=$SERVICE
HOME_DIR="/srv/${SERVICE}"
REPO_DIR="${HOME_DIR}/repo"
COMPOSE_DIR="${REPO_DIR}/sentiment_api"
ENV_FILE="/etc/${SERVICE}/env"
POSTGRES_UID=999
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKIP_USER=false
SKIP_REPO=false
SERVICE_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --skip-user) SKIP_USER=true ;;
    --skip-repo) SKIP_REPO=true ;;
    --service-only) SERVICE_ONLY=true ;;
  esac
done

if $SERVICE_ONLY; then
  echo "[*] Creating systemd service only (--service-only)"
  exec "$SCRIPT_DIR/create-service.sh" --enable
fi

echo "[*] sentiment_api deployment (user: $USER, home: $HOME_DIR)"

# -----------------------------------------------------------------------------
# 1. Dedicated service user
# -----------------------------------------------------------------------------
if ! $SKIP_USER; then
  echo "[*] Creating user $USER and directory layout..."
  if ! getent passwd "$USER" >/dev/null; then
    useradd --system --create-home --home-dir "$HOME_DIR" --shell /usr/sbin/nologin "$USER"
    usermod -aG docker "$USER"
    loginctl enable-linger "$USER" 2>/dev/null || true
  fi

  mkdir -p "${HOME_DIR}/volumes/postgres/data"
  mkdir -p "${HOME_DIR}/volumes/redis"
  mkdir -p "${HOME_DIR}/volumes/weaviate"
  mkdir -p "${HOME_DIR}/volumes/artifacts"
  mkdir -p "${HOME_DIR}/volumes/logs"
  mkdir -p "${HOME_DIR}/volumes/reports"
  mkdir -p "${HOME_DIR}/volumes/embedding_cache"
  mkdir -p "${HOME_DIR}/volumes/grafana_data"
  mkdir -p "${HOME_DIR}/volumes/loki_data"

  chown -R "$USER:$USER" "$HOME_DIR"
  chown -R "$POSTGRES_UID:$POSTGRES_UID" "${HOME_DIR}/volumes/postgres/data" 2>/dev/null || true
  chmod 700 "${HOME_DIR}/volumes/postgres/data"
  # Copy universe CSVs from repo artifacts into volume if missing (so containers can seed from them)
  ARTIFACTS_SRC="${COMPOSE_DIR}/artifacts"
  ARTIFACTS_VOL="${HOME_DIR}/volumes/artifacts"
  for f in sp500.csv nasdaq100.csv sectors.csv industries.csv; do
    if [[ -f "$ARTIFACTS_SRC/$f" ]] && [[ ! -f "$ARTIFACTS_VOL/$f" ]]; then
      cp "$ARTIFACTS_SRC/$f" "$ARTIFACTS_VOL/$f"
      chown "$USER:$USER" "$ARTIFACTS_VOL/$f"
      chmod 644 "$ARTIFACTS_VOL/$f"
    fi
  done
  chown "$USER:$USER" "$ARTIFACTS_VOL" 2>/dev/null || true
  chmod 755 "$ARTIFACTS_VOL"
  # Grafana and Loki run as non-root in container; host dirs must match
  chown -R 472:472 "${HOME_DIR}/volumes/grafana_data" 2>/dev/null || true
  chmod 700 "${HOME_DIR}/volumes/grafana_data"
  chown -R 10001:10001 "${HOME_DIR}/volumes/loki_data" 2>/dev/null || true
  chmod 700 "${HOME_DIR}/volumes/loki_data"

  echo "[+] User and directories created"
fi

# -----------------------------------------------------------------------------
# 2. Secrets and environment
# -----------------------------------------------------------------------------
mkdir -p "/etc/${SERVICE}"
if [[ ! -f "$ENV_FILE" ]]; then
  touch "$ENV_FILE"
  chown "$USER:$USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "[+] Created $ENV_FILE — edit with DATABASE_URL, REDIS_URL, OPENAI_API_KEY, SENTIMENT_API_API_KEYS"
else
  echo "[*] $ENV_FILE already exists"
fi

# -----------------------------------------------------------------------------
# 3. Repository checkout
# -----------------------------------------------------------------------------
if ! $SKIP_REPO; then
  echo "[*] Repository checkout..."
  if [[ -d "$REPO_DIR/.git" ]]; then
    echo "[*] Repo exists at $REPO_DIR; skipping clone. Use --skip-repo for updates."
  else
    echo "    Run manually as $USER:"
    echo "    sudo -u $USER ssh-keygen -t ed25519 -f ${HOME_DIR}/.ssh/id_ed25519 -N ''"
    echo "    sudo -u $USER git clone https://github.com/sickboycz/sentimenter_api.git $REPO_DIR"
    echo "    Then re-run this script"
    exit 1
  fi
fi

# -----------------------------------------------------------------------------
# 4. Build and first start
# -----------------------------------------------------------------------------
if [[ ! -d "$COMPOSE_DIR" ]]; then
  echo "[!] Compose dir not found: $COMPOSE_DIR"
  echo "    Ensure repo contains sentiment_api/"
  exit 1
fi

echo "[*] Building and starting (postgres + redis first)..."

sudo -u "$USER" bash -c "
  cd $COMPOSE_DIR
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml build --no-cache
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml up -d postgres redis
"

echo "[*] Waiting for postgres..."
sleep 10
until (cd "$COMPOSE_DIR" && docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres pg_isready -U sentiment) 2>/dev/null; do
  echo "    Waiting..."
  sleep 3
done

# -----------------------------------------------------------------------------
# 5. Database init
# -----------------------------------------------------------------------------
SCHEMA="${REPO_DIR}/Docs/sentiment_api_tech_package_v1.1/db/schema.sql"
if [[ -f "$SCHEMA" ]]; then
  echo "[*] Applying schema..."
  (cd "$COMPOSE_DIR" && docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres psql -U sentiment -d sentiment) < "$SCHEMA" 2>/dev/null || {
    echo "[!] Schema apply failed; postgres may already be initialized. Continuing."
  }
else
  echo "[!] Schema not found: $SCHEMA"
fi

# -----------------------------------------------------------------------------
# 6. Start all services
# -----------------------------------------------------------------------------
echo "[*] Starting all services..."
sudo -u "$USER" bash -c "
  cd $COMPOSE_DIR
  docker compose --env-file $ENV_FILE -f docker-compose.yml -f docker-compose.production.yml up -d
"

# -----------------------------------------------------------------------------
# 7. Systemd unit (optional)
# -----------------------------------------------------------------------------
UNIT_FILE="/etc/systemd/system/sentimenter-docker.service"
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
echo "[+] Systemd unit: $UNIT_FILE (enable with: systemctl enable sentimenter-docker)"

# -----------------------------------------------------------------------------
# 8. Permissions and verification
# -----------------------------------------------------------------------------
SCRIPT_PARENT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ -x "$SCRIPT_PARENT/check-permissions.sh" ]]; then
  echo "[*] Checking permissions (run with --fix to repair)..."
  "$SCRIPT_PARENT/check-permissions.sh" 2>/dev/null || true
fi
echo ""
echo "[*] Verification:"
echo "    docker compose ps"
echo "    curl -s http://127.0.0.1:8080/v1/health | head"
echo "    sudo $SCRIPT_PARENT/check-permissions.sh --fix   # fix permissions if needed"
echo ""
echo "[+] Done. Edit $ENV_FILE with secrets, then: sudo systemctl restart sentimenter-docker"
