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
    ├── weaviate/
    ├── artifacts/
    ├── logs/
    ├── reports/
    ├── embedding_cache/
    ├── grafana_data/
    └── loki_data/
```

---

## 4. Permissions and volume directories

Create volume directories (if not using `install.sh`, which creates them):

```bash
sudo mkdir -p /srv/sentimenter/volumes/postgres/data \
  /srv/sentimenter/volumes/redis \
  /srv/sentimenter/volumes/weaviate \
  /srv/sentimenter/volumes/artifacts \
  /srv/sentimenter/volumes/logs \
  /srv/sentimenter/volumes/reports \
  /srv/sentimenter/volumes/embedding_cache \
  /srv/sentimenter/volumes/grafana_data \
  /srv/sentimenter/volumes/loki_data
```

Set ownership:

```bash
sudo chown -R sentimenter:sentimenter /srv/sentimenter
sudo chown -R 999:999 /srv/sentimenter/volumes/postgres/data
sudo chmod 700 /srv/sentimenter/volumes/postgres/data
```

Postgres runs as UID 999 inside the container; the host directory must be owned accordingly. Grafana and Loki use fixed UIDs in their images; if you create their dirs manually, you may need `chown 472:472` (grafana_data) and `chown 10001:10001` (loki_data). The deployment script `install.sh` handles this.

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
| weaviate | `/srv/sentimenter/volumes/weaviate` | `/var/lib/weaviate` |
| api, worker | `/srv/sentimenter/volumes/artifacts` | `/data/artifacts` |
| api, worker, daemon | `/srv/sentimenter/volumes/logs` | `/data/logs` |
| api, worker | `/srv/sentimenter/volumes/embedding_cache` | `/var/lib/sentiment_api` (2-tier retrieval SQLite cache) |
| grafana | `/srv/sentimenter/volumes/grafana_data` | `/var/lib/grafana` |
| loki | `/srv/sentimenter/volumes/loki_data` | `/loki` |

---

## 8. First build and start

### Option A: Deployment script

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./install.sh              # first time
# Or, if user/dirs or repo already exist:
sudo ./install.sh --skip-user   # user/dirs already exist
sudo ./install.sh --skip-repo   # repo already cloned
```

After the stack is up, run **seed universes** and **create API key** (same as Option B steps 3–6 below), then add the printed key to `/etc/sentimenter/env` as `SENTIMENT_API_API_KEYS=...` and restart.

### Option B: Manual

```bash
cd /srv/sentimenter/repo/sentiment_api
ENV_FILE="/etc/sentimenter/env"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file $ENV_FILE"

# Build and start postgres + redis first
sudo -u sentimenter $COMPOSE build --no-cache
sudo -u sentimenter $COMPOSE up -d postgres redis

# Wait for postgres
sleep 15
until docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres pg_isready -U sentiment 2>/dev/null; do sleep 2; done

# 1. Apply DB schema (migrations)
./scripts/apply_schema_from_zero.sh

# 2. Start API so we can run seed and create-key inside container
sudo -u sentimenter $COMPOSE up -d

# 3. Seed universes (no uv required — runs inside API container)
docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file $ENV_FILE exec api python -c "
import asyncio
from sentiment_api.universe.refresh import refresh_universes
print(asyncio.run(refresh_universes()))
"

# 4. Create API key (no uv required — runs inside API container)
# Copy the printed key and add to /etc/sentimenter/env as SENTIMENT_API_API_KEYS=key_here
docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file $ENV_FILE exec api python -c "
import asyncio, secrets
from sentiment_api.db.pool import init_pool, acquire
from sentiment_api.config import get_settings
from argon2 import PasswordHasher
async def main():
    s = get_settings()
    await init_pool(s.database_url)
    key = secrets.token_urlsafe(32)
    h = PasswordHasher().hash(key)
    async with acquire() as c:
        await c.execute('''INSERT INTO api_keys (name, key_hash, enabled, rate_limit_per_min, notes) VALUES (\$1, \$2, true, 120, \$3)''', 'default', h, 'Bootstrap key')
    print('API key (add to /etc/sentimenter/env as SENTIMENT_API_API_KEYS=...):')
    print(key)
asyncio.run(main())
"

# 5. Edit /etc/sentimenter/env: add SENTIMENT_API_API_KEYS=<the key printed above>
# 6. Restart so API loads the new key
sudo systemctl restart sentimenter-docker   # or: sudo -u sentimenter $COMPOSE up -d --force-recreate api
```

### Systemd (optional)

```bash
sudo systemctl enable sentimenter-docker
sudo systemctl start sentimenter-docker
```

---

## 9. Database migrations (if applicable)

sentiment_api uses SQL migrations (no Alembic). Apply in order:

```bash
cd /srv/sentimenter/repo/sentiment_api
./scripts/apply_schema_from_zero.sh
```

This applies: `00_base_schema.sql` → `v1.1_add_universes.sql` → `v1.1_asset_targeting_audit.sql` → `v1.1_retention_tombstone.sql`. Scripts are idempotent (safe to re-run). See `migrations/README.md` for details. If the DB was created with the old single schema file (`Docs/.../schema.sql`), run only the three `v1.1_*.sql` files (see `migrations/README.md`).

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

## 10.5 Ingestion pipeline (how it runs)

When the stack is up, the **daemon** and **worker** containers are already running:

- **Daemon** — Polls enabled sources (RSS, GDELT, scrape) from `registry/source_registry.yaml` every **update_interval_sec** (default 300). Pushes raw items to the Redis ingest queue.
- **Worker** — Consumes the queue: normalize → cluster → summarize → score → index. Writes articles, clusters, embeddings, and runs to Postgres.

No extra start step: ingestion runs automatically. To confirm and optionally trigger a run immediately:

**1. Check daemon and worker are up**
```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file /etc/sentimenter/env ps
# daemon and worker should be "Up" or "running"
```

**2. Trigger one poll cycle now (optional)**  
Instead of waiting for the next interval, trigger a run via the API (use an API key from `/etc/sentimenter/env`):

```bash
curl -s -X POST "http://127.0.0.1:8080/v1/admin/ingest/run" -H "X-API-Key: YOUR_KEY"
# Optional: ?source_id=gdelt_doc_v2 to poll only one source
```

**3. Verify ingestion**
```bash
# Daemon/worker logs
docker compose -f docker-compose.yml -f docker-compose.production.yml logs -f daemon
docker compose -f docker-compose.yml -f docker-compose.production.yml logs -f worker

# Article count (after a few minutes)
docker compose -f docker-compose.yml -f docker-compose.production.yml exec postgres \
  psql -U sentiment -d sentiment -c "SELECT COUNT(*) FROM articles;"
```

**4. Backfill historical data (optional)**  
To backfill a date range (e.g. last 7 days):

```bash
curl -s -X POST "http://127.0.0.1:8080/v1/admin/backfill" -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" -d '{"from":"2026-01-27","to":"2026-02-02"}'
```

Or inside the API container:  
`docker compose ... exec api sentiment-api backfill --from 2026-01-27 --to 2026-02-02`

Ensure **OPENAI_API_KEY** is set in `/etc/sentimenter/env` if you use summarization/embeddings; otherwise worker steps that call OpenAI may fail.

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

## 13. Troubleshooting

### Permissions

- **Postgres data dir:** Must be owned by UID 999 (Postgres in container).  
  `sudo chown -R 999:999 /srv/sentimenter/volumes/postgres/data && sudo chmod 700 /srv/sentimenter/volumes/postgres/data`
- **Compose / env file:** Run `docker compose` as user `sentimenter` so it can read `/etc/sentimenter/env`.  
  `sudo chown sentimenter:sentimenter /etc/sentimenter/env && sudo chmod 600 /etc/sentimenter/env`
- **Volume dirs:** All under `/srv/sentimenter/volumes/` should be owned by `sentimenter` (except postgres/data as above).  
  `sudo chown -R sentimenter:sentimenter /srv/sentimenter/volumes`
- **Grafana / Loki:** If you created their dirs manually, use `chown 472:472` (grafana_data) and `chown 10001:10001` (loki_data). The `install.sh` script does this.

### `uv: command not found`

You do not need `uv` on the server. Seed universes and create API key **inside the API container** (see section 8, Option B, steps 3–4):

```bash
cd /srv/sentimenter/repo/sentiment_api
docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file /etc/sentimenter/env exec api python -c "
import asyncio; from sentiment_api.universe.refresh import refresh_universes; print(asyncio.run(refresh_universes()))
"
# Create API key: run the longer python -c "..." block from section 8 Option B step 4.
```

### Registry file not found

Worker or daemon fails with "Registry file not found". Do **not** set `SOURCE_REGISTRY_PATH` in `/etc/sentimenter/env` unless you use exactly:  
`SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml`.  
The Compose stack mounts the registry at that path; wrong paths (e.g. `Docs/...`) cause this error.

### API key not working

- Ensure the key is in `/etc/sentimenter/env`: `SENTIMENT_API_API_KEYS=your_key_here` (comma-separated for multiple).
- Restart the API after changing env: `sudo systemctl restart sentimenter-docker` or `docker compose ... up -d --force-recreate api`.
- Create a new key with the "Create API key" command in section 8 (Option B step 4) if the old one was lost.

### Connection refused / service not up

- Check containers: `docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file /etc/sentimenter/env ps`.
- Start stack: `sudo -u sentimenter docker compose ... up -d` (from `sentiment_api/`).
- Ensure postgres is ready before migrations: `docker compose ... exec postgres pg_isready -U sentiment`.

### Web UI: CORS / "blocked by CORS policy" or "loopback" when opening by IP

When you open the UI at **http://YOUR_SERVER_IP:3000** (e.g. http://80.211.210.49:3000), the browser must call the API at the **same host**, not `localhost`.

**Auto-detection:** If you do *not* set `NEXT_PUBLIC_API_BASE_URL`, the frontend uses the same host as the page with port 8080 (e.g. page at http://80.211.210.49:3000 → API at http://80.211.210.49:8080). For same-host deployments you only need to allow the frontend origin in CORS and rebuild.

1. **Set CORS** (and optionally API URL) in `/etc/sentimenter/env` (replace with your server IP or hostname):
   ```bash
   # Required so the API accepts requests from the UI origin
   CORS_ORIGINS=http://80.211.210.49:3000
   # Optional: only if the API is on a different host/port
   # NEXT_PUBLIC_API_BASE_URL=http://80.211.210.49:8080
   ```

2. **Rebuild the frontend** (so CORS and any API URL are applied):
   ```bash
   cd /srv/sentimenter/repo/sentiment_api
   sudo -u sentimenter docker compose -f docker-compose.yml -f docker-compose.production.yml \
     --env-file /etc/sentimenter/env build --no-cache frontend
   ```

3. **Restart the stack** so the API loads the new CORS origins:
   ```bash
   sudo systemctl restart sentimenter-docker
   ```
   Or: `docker compose ... up -d --force-recreate api frontend`

Then open **http://YOUR_SERVER_IP:3000** again; the UI will call **http://YOUR_SERVER_IP:8080** and CORS will allow it.

### Migrations fail (relation already exists, etc.)

If the DB was created with the old single schema file, do **not** run `apply_schema_from_zero.sh` (base would conflict). Run only the v1.1 migrations:

```bash
cd /srv/sentimenter/repo/sentiment_api
for f in migrations/v1.1_add_universes.sql migrations/v1.1_asset_targeting_audit.sql migrations/v1.1_retention_tombstone.sql; do
  docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres psql -U sentiment -d sentiment -f - < "$f"
done
```

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| API | 8080 | REST API |
| Frontend | 3000 | Next.js dashboard |
| Weaviate | 8081 | Vector store (optional) |
| Prometheus | 9090 | Metrics |
| Grafana | 3001 | Dashboards (admin/admin) |
| Postgres | 5432 | Database |
| Redis | 6379 | Queue/cache |
