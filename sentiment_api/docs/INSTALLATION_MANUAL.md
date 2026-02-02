# sentiment_api — Installation & Update Manual (Production)

**Version:** 1.2  
**Date:** 2026-02-02  
**Guidelines:** Generic Service Installation and Update Manual v2  
**Service user:** `sentimenter`  
**Data location:** `/srv/sentimenter/volumes/` (out-of-Docker, never inside repo)

Production-grade procedure for installing, operating, and updating the sentiment_api Docker-based service on Ubuntu 22.04+.

---

## 1. System prerequisites

- **Ubuntu 22.04 LTS+**
- **Docker Engine** + **Docker Compose v2**
- **systemd**
- **Outbound HTTPS** (for API sources, OpenAI, etc.)
- **Python 3.11+** (for local dev; Docker uses images)

### Python dependencies

```bash
# With uv (recommended)
uv sync

# With pip
pip install -r requirements.txt
```

- `requirements.txt` — production deps (generated from `uv export --no-dev`)
- `requirements-dev.txt` — includes pytest (generated from `uv export --extra dev`)

Install Docker:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable docker && sudo systemctl start docker
```

---

## 2. Dedicated service user

Run the service under a non-login system user.

```bash
sudo useradd --system --create-home --home-dir /srv/sentimenter --shell /usr/sbin/nologin sentimenter
sudo usermod -aG docker sentimenter
sudo loginctl enable-linger sentimenter
```

---

## 3. Directory layout (data never inside repo)

```
/srv/sentimenter/
├── repo/                    # Git checkout (Sentimenter root)
│   ├── Docs/
│   └── sentiment_api/
└── volumes/                 # Data outside Docker
    ├── postgres/
    │   └── data/
    ├── redis/
    ├── artifacts/
    ├── logs/
    ├── reports/
    ├── grafana_data/
    └── loki_data/
```

---

## 4. Permissions

```bash
sudo chown -R sentimenter:sentimenter /srv/sentimenter
sudo chown -R 999:999 /srv/sentimenter/volumes/postgres/data
sudo chmod 700 /srv/sentimenter/volumes/postgres/data
```

Postgres runs as UID 999 inside the container; the host directory must be owned accordingly.

---

## 5. Secrets and environment

Keep secrets outside the repository.

```bash
sudo mkdir -p /etc/sentimenter
sudo touch /etc/sentimenter/env
sudo chown sentimenter:sentimenter /etc/sentimenter/env
sudo chmod 600 /etc/sentimenter/env
```

Edit `/etc/sentimenter/env`:

```bash
# Database (Docker internal hostnames)
DATABASE_URL=postgresql://sentiment:SECRET@postgres:5432/sentiment

# Redis
REDIS_URL=redis://redis:6379/0

# API keys (comma-separated)
SENTIMENT_API_API_KEYS=prod_key_xxx,another_key_yyy

# OpenAI (optional)
OPENAI_API_KEY=sk-xxx

# Environment
SENTIMENT_API_ENV=production
```

**Do not set** `SOURCE_REGISTRY_PATH` in this file when using Docker Compose — the stack mounts the registry at `/etc/sentiment_api/source_registry.yaml`. If you set it, use exactly: `SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml`. Wrong paths (e.g. `Docs/...`) will make worker and daemon fail with "Registry file not found".

**Important:** Do not commit secrets to the repo.

---

## 6. Repository checkout (SSH)

```bash
sudo -u sentimenter ssh-keygen -t ed25519 -f /srv/sentimenter/.ssh/id_ed25519 -N ''
# Add /srv/sentimenter/.ssh/id_ed25519.pub to your Git provider

sudo -u sentimenter git clone https://github.com/sickboycz/sentimenter_api.git /srv/sentimenter/repo
```

---

## 7. Docker Compose override (bind mounts)

Production uses bind mounts so data lives outside the repo. The file `sentiment_api/docker-compose.production.yml` overrides volumes:

| Container | Host path | Container path |
|-----------|-----------|----------------|
| postgres | `/srv/sentimenter/volumes/postgres/data` | `/var/lib/postgresql/data` |
| redis | `/srv/sentimenter/volumes/redis` | `/data` |
| api, worker, daemon | `/srv/sentimenter/volumes/artifacts` | `/data/artifacts` |
| api, worker, daemon | `/srv/sentimenter/volumes/logs` | `/data/logs` |
| grafana | `/srv/sentimenter/volumes/grafana_data` | `/var/lib/grafana` |
| loki | `/srv/sentimenter/volumes/loki_data` | `/loki` |

---

## 8. First build and start

### Option A: Deployment script

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./install.sh --skip-user   # if user/dirs already exist
sudo ./install.sh --skip-repo   # if repo already cloned
```

### Option B: Manual

```bash
cd /srv/sentimenter/repo/sentiment_api

sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env build --no-cache

# Start postgres + redis first
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env up -d postgres redis

# Wait for postgres
sleep 15

# Init DB
docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
  psql -U sentiment -d sentiment < /srv/sentimenter/repo/Docs/sentiment_api_tech_package_v1.1/db/schema.sql

# Start all services
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env up -d
```

### Systemd (optional)

```bash
sudo systemctl enable sentimenter-docker
sudo systemctl start sentimenter-docker
```

---

## 9. Database migrations (if applicable)

sentiment_api uses SQL schema + migrations, not Alembic:

```bash
cd /srv/sentimenter/repo/sentiment_api

# Apply additional migrations
for f in migrations/*.sql; do
  docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
    psql -U sentiment -d sentiment -f - < "$f"
done
```

---

## 10. Verification checklist

```bash
cd /srv/sentimenter/repo/sentiment_api
docker compose -f docker-compose.yml -f docker-compose.production.yml ps

curl -s http://127.0.0.1:8080/v1/health
curl -s http://127.0.0.1:8080/ready
curl -s http://127.0.0.1:9090/-/ready   # Prometheus
curl -s http://127.0.0.1:3001/api/health # Grafana (admin/admin)
```

---

## 11. Updating the service (safe)

Repeatable, no data loss.

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git fetch --all
sudo -u sentimenter git pull

cd sentiment_api
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env build --no-cache
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env up -d

sudo systemctl restart sentimenter-docker
```

Or use the update script:

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./update.sh
```

### 11.5 Rollback

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git reset --hard HEAD~1

cd sentiment_api
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env build --no-cache
sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
  --env-file /etc/sentimenter/env up -d

sudo systemctl restart sentimenter-docker
```

Or:

```bash
sudo ./scripts/deploy/rollback.sh
```

---

## 12. Operational principles

- **systemd** controls lifecycle (when using `sentimenter-docker.service`).
- **Docker Compose** never stores secrets; use `/etc/sentimenter/env`.
- **Repositories** are disposable; data lives in `/srv/sentimenter/volumes/`.
- **Out-of-Docker DB files** ensure Postgres and Redis data persist outside containers.

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| API | 8080 | REST API |
| Frontend | 3000 | Next.js dashboard |
| Prometheus | 9090 | Metrics |
| Grafana | 3001 | Dashboards (admin/admin) |
| Postgres | 5432 | Database |
| Redis | 6379 | Queue/cache |
