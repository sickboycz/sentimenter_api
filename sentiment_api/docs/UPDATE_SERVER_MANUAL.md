# sentiment_api — Update on One Server

**Purpose:** Step-by-step manual to update the sentiment_api deployment on a single server.  
**User:** `sentimenter` | **Data:** `/srv/sentimenter/volumes/` | **Repo:** `/srv/sentimenter/repo`

---

## What to do now — Upgrade steps (quick reference)

After pulling code or config changes on the server:

| Change type | Steps |
|-------------|--------|
| **Any code / compose / env** | Pull → [Rebuild and restart](#step-3-rebuild-and-restart) → [Restart systemd](#step-4-restart-systemd-if-used) |
| **Registry only** (`registry/source_registry.yaml`) | Pull → Restart stack (registry is mounted; no image rebuild needed): `docker compose ... up -d` then `sudo systemctl restart sentimenter-docker` |
| **Frontend only** (UI / CORS / API URL) | Pull → Rebuild frontend: `docker compose ... build --no-cache frontend` → `docker compose ... up -d` → restart systemd |
| **New DB migrations** | After deploy, [run migrations](INSTALLATION_MANUAL.md#migrations) (e.g. `scripts/apply_schema_from_zero.sh` for fresh DB, or apply only new `migrations/v1.1_*.sql` files). |

**One-liner (full upgrade):**

```bash
cd /srv/sentimenter/repo && sudo -u sentimenter git pull && cd sentiment_api && \
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env -f docker-compose.yml -f docker-compose.production.yml build --no-cache && \
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env -f docker-compose.yml -f docker-compose.production.yml up -d && \
sudo systemctl restart sentimenter-docker
```

Or use the script: `cd /srv/sentimenter/repo/sentiment_api/scripts/deploy && sudo ./update.sh`

---

## 1. Prerequisites

- Server with Docker + Docker Compose
- Repo cloned at `/srv/sentimenter/repo`
- Secrets in `/etc/sentimenter/env`
- Production: `docker-compose.production.yml` in use (data in `/srv/sentimenter/volumes/`)

---

## 2. Update Procedure (Manual)

### Step 1: SSH to server

```bash
ssh root@IBKR-Trading-Bot
# or: ssh your_user@your-server
```

### Step 2: Fetch and pull

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git fetch --all
sudo -u sentimenter git pull
```

**If you're unsure pull worked** (e.g. old files still there, missing new files): ensure you're on the right branch and match the remote exactly:

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git fetch origin
sudo -u sentimenter git status          # see branch and "Your branch is up to date" or "behind"
sudo -u sentimenter git pull           # or: git reset --hard origin/prod-v1.1.1  (discards local changes)
```

Use `git reset --hard origin/<branch>` only if you want to **discard all local changes** and match the remote exactly (e.g. branch is `prod-v1.1.1`).

### Step 2.1: Verify required files (after pull)

These paths must exist under `/srv/sentimenter/repo/sentiment_api/` for the stack to run:

| Path | Purpose |
|------|---------|
| `registry/source_registry.yaml` | Source registry (compose mounts it into containers) |
| `docker-compose.yml` | Main compose |
| `docker-compose.production.yml` | Production override |
| `migrations/v1.1_add_universes.sql` | DB migrations (sectors, etc.) |
| `infra/prometheus/prometheus.yml` | Prometheus config |
| `infra/grafana/` | Grafana provisioning/dashboards |
| `infra/loki/loki-config.yaml` | Loki config |

Quick check on the server (or run the verify script with optional pull):

```bash
cd /srv/sentimenter/repo/sentiment_api
test -f registry/source_registry.yaml && test -f docker-compose.yml && test -f docker-compose.production.yml && echo "OK: required files present" || echo "MISSING: check paths above"
# Or: cd scripts/deploy && sudo ./verify-repo.sh --pull
```

**Base DB schema** (first-time init): if you use the install script, it looks for `../Docs/sentiment_api_tech_package_v1.1/db/schema.sql` (i.e. `/srv/sentimenter/repo/Docs/...`). That folder lives in the **full** repo (Sentimenter root with `Docs/` and `sentiment_api/`). If your clone has no `Docs/`, apply the base schema from another source or use migrations only on an already-initialized DB.

### Step 3: Rebuild and restart

```bash
cd /srv/sentimenter/repo/sentiment_api

sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml build --no-cache

sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

### Step 4: Restart systemd (if used)

```bash
sudo systemctl restart sentimenter-docker
```

### Step 5: Verify

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml ps
curl -s http://127.0.0.1:8080/v1/health | head
docker logs sentiment_api-worker-1 --tail 20
docker logs sentiment_api-daemon-1 --tail 20
```

---

## 3. Update Script (Alternative)

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./update.sh
```

The script: `git fetch` → `git pull` → `docker compose build --no-cache` → `docker compose up -d` → `systemctl restart sentimenter-docker`.

---

## 4. Rollback

If the update fails or introduces issues:

### Option A: Rollback script

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./rollback.sh
```

### Option B: Manual rollback

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git reset --hard HEAD~1

cd sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml build --no-cache
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d

sudo systemctl restart sentimenter-docker
```

### Option C: Rollback to tagged release

```bash
cd /srv/sentimenter/repo
sudo -u sentimenter git fetch --tags
sudo -u sentimenter git checkout v1.1.1   # or prod-v1.1.1

cd sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml build --no-cache
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

---

## 5. Checklist

| Step | Command / Check |
|------|------------------|
| 1 | `cd /srv/sentimenter/repo` |
| 2 | `sudo -u sentimenter git pull` |
| 3 | `cd sentiment_api` |
| 4 | `docker compose ... build --no-cache` |
| 5 | `docker compose ... up -d` |
| 6 | `systemctl restart sentimenter-docker` |
| 7 | `curl http://127.0.0.1:8080/v1/health` |
| 8 | `docker logs sentiment_api-worker-1 --tail 10` |
| 9 | `docker logs sentiment_api-daemon-1 --tail 10` |

---

## 6. Troubleshooting

### 6.1 Service was never created (install failed earlier)

If installation failed before the systemd unit was created (e.g. build or compose up failed), create the service afterward:

```bash
cd /srv/sentimenter/repo/sentiment_api/scripts/deploy
sudo ./create-service.sh --enable
```

Or re-run install with service-only (same effect):

```bash
sudo ./install.sh --service-only
```

Then start the stack and the service:

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
sudo systemctl start sentimenter-docker
```

### 6.2 `sentimenter-docker.service` failed to start

On the server, get the real error:

```bash
systemctl status sentimenter-docker.service
journalctl -xeu sentimenter-docker.service --no-pager
```

Then try running what the unit runs, as user `sentimenter`:

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

| Likely cause | Fix |
|--------------|-----|
| **Permission denied** (Docker socket) | Ensure `sentimenter` is in the `docker` group: `sudo usermod -aG docker sentimenter`; then log out/in or reboot. |
| **Cannot read /etc/sentimenter/env** | Ensure file exists and is readable by `sentimenter`: `sudo chown root:sentimenter /etc/sentimenter/env && sudo chmod 640 /etc/sentimenter/env`. |
| **WorkingDirectory / path** | Unit uses `WorkingDirectory=/srv/sentimenter/repo/sentiment_api`. If your repo is elsewhere, edit the unit: `sudo systemctl edit --full sentimenter-docker` and fix `WorkingDirectory` and `ExecStart`. |
| **`docker compose` not found** | Install Docker Compose plugin or use standalone `docker-compose`; then ensure the unit’s `ExecStart` matches (e.g. `docker-compose` instead of `docker compose`). |

If you fix the unit file (e.g. add `--env-file /etc/sentimenter/env` to `ExecStart`), reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart sentimenter-docker
```

### 6.3 Other issues

| Symptom | Action |
|---------|--------|
| `Registry file not found: Docs/...` | `/etc/sentimenter/env` is overriding with a wrong path. Remove `SOURCE_REGISTRY_PATH` from that file, or set `SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml`. Then restart: `docker compose ... up -d` and `systemctl restart sentimenter-docker`. |
| `Registry file not found` (other) | Ensure `registry/source_registry.yaml` exists in repo; docker-compose sets `SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml` |
| Worker/daemon crash loop | Check logs: `docker logs sentiment_api-worker-1`; verify Postgres + Redis healthy |
| `git pull` fails | Check SSH key / auth; `sudo -u sentimenter git status` |
| Build fails | `docker compose build --no-cache`; check Dockerfile, pyproject.toml |
| Port conflict | Stop other stacks: `docker compose down` (from other compose dirs) |
| Prometheus unhealthy / dependency failed | Check logs: `docker logs sentiment_api-prometheus-1`. Ensure `infra/prometheus/prometheus.yml` is valid; healthcheck uses `wget --spider` on `/-/ready` with 30s start_period. |
| **Redis or Postgres failed to start** (dependency failed, exited 0) | See [6.4 Redis / Postgres won't start](#64-redis--postgres-wont-start). |
| **relation "sectors" does not exist** (Postgres ERROR) | Database migrations not applied. See [6.5 Apply database migrations](#65-apply-database-migrations). |
| **relation "sources" does not exist** (worker/API) | Base schema was never applied. Apply base schema first (see [6.5](#65-apply-database-migrations): base schema from `Docs/.../db/schema.sql`), then v1.1 migrations, then restart stack. |
| **API failed to start** (dependency failed: sentiment_api-api-1 exited 0) | Check API logs: `docker logs sentiment_api-api-1`. Fix the reported error (e.g. missing schema → [6.5](#65-apply-database-migrations), registry path → remove/wrong SOURCE_REGISTRY_PATH in `/etc/sentimenter/env`). |
| **Files missing / pull didn't bring new files** | See [Step 2.1](#step-21-verify-required-files-after-pull). Run `git fetch origin && git status`; if behind, run `git pull`. To match remote exactly (discard local changes): `git reset --hard origin/<branch>`. Then re-check required files under `sentiment_api/`. |
| **Grafana or Loki restart loop** (permission denied on `/loki/rules` or `/var/lib/grafana`) | See [6.6 Grafana / Loki restart (permission denied)](#66-grafana--loki-restart-permission-denied). chown volumes to 472 (grafana) and 10001 (loki). |

### 6.4 Redis / Postgres won't start

If you see `dependency failed to start: container sentiment_api-redis-1 exited (0)` or Postgres failing:

**1. Get the real error from the containers**

```bash
docker logs sentiment_api-redis-1
docker logs sentiment_api-postgres-1
```

**2. Fix volume permissions (most common cause)**

Postgres requires the data directory to be owned by UID 999 and not writable by others. Redis needs a writable `/data` (volume).

```bash
# Postgres: UID 999, mode 700
sudo chown -R 999:999 /srv/sentimenter/volumes/postgres/data
sudo chmod 700 /srv/sentimenter/volumes/postgres/data

# Redis: writable by container (Redis often runs as UID 999 or 1000)
sudo chown -R 999:999 /srv/sentimenter/volumes/redis
sudo chmod 700 /srv/sentimenter/volumes/redis
```

If Redis still fails, try making the redis volume world-writable temporarily to confirm it's permissions: `sudo chmod 777 /srv/sentimenter/volumes/redis` (then lock it down again once it works).

**3. Check for port conflicts**

Another process may be using 5432 or 6379:

```bash
ss -tlnp | grep -E '5432|6379'
# or: sudo lsof -i :5432 -i :6379
```

Stop the other service or change the compose ports if needed.

**4. Restart the stack**

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

### 6.5 Apply database migrations

If the worker fails with **relation "sources" does not exist**, the **base schema** was never applied. If you see **relation "sectors" does not exist**, the **v1.1 migrations** were not applied. Apply in order: base schema first, then v1.1 migrations.

**1. Apply schema from zero** (recommended: self-contained, no Docs/ required)

```bash
cd /srv/sentimenter/repo/sentiment_api
./scripts/apply_schema_from_zero.sh
```

This runs `migrations/00_base_schema.sql` then the v1.1 migrations in order. Safe to re-run.

**Alternative: base schema from Docs/** (only if you have the full repo with `Docs/`)

```bash
if [ -f /srv/sentimenter/repo/Docs/sentiment_api_tech_package_v1.1/db/schema.sql ]; then
  docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
    psql -U sentiment -d sentiment -f /dev/stdin < /srv/sentimenter/repo/Docs/sentiment_api_tech_package_v1.1/db/schema.sql
fi
```

**2. Apply migrations** (only if you did not use apply_schema_from_zero.sh; creates sectors, universes, etc.)

```bash
cd /srv/sentimenter/repo/sentiment_api

for f in migrations/v1.1_add_universes.sql migrations/v1.1_asset_targeting_audit.sql migrations/v1.1_retention_tombstone.sql; do
  [ -f "$f" ] && docker compose -f docker-compose.yml -f docker-compose.production.yml exec -T postgres \
    psql -U sentiment -d sentiment -f - < "$f" && echo "Applied $f"
done
```

**3. Restart API/worker/daemon** so they pick up the schema

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

### 6.6 Grafana / Loki restart (permission denied)

If Grafana or Loki are in a restart loop and logs show **permission denied** on their data dir (e.g. Loki: `stat /loki/rules: permission denied`), fix volume ownership. The containers run as non-root:

- **Grafana** runs as UID **472**
- **Loki** runs as UID **10001**

On the server:

```bash
sudo chown -R 472:472 /srv/sentimenter/volumes/grafana_data
sudo chmod 700 /srv/sentimenter/volumes/grafana_data

sudo chown -R 10001:10001 /srv/sentimenter/volumes/loki_data
sudo chmod 700 /srv/sentimenter/volumes/loki_data
```

Then restart the stack:

```bash
cd /srv/sentimenter/repo/sentiment_api
sudo -u sentimenter docker compose --env-file /etc/sentimenter/env \
  -f docker-compose.yml -f docker-compose.production.yml up -d
```

---

## 7. Docker volumes (production)

With `docker-compose.production.yml`, **all persistent data** is on the host under `/srv/sentimenter/volumes/` (bind mounts). There are no Docker named volumes in production.

| Host path | Container path / use | Service |
|-----------|----------------------|---------|
| `/srv/sentimenter/volumes/postgres/data` | `/var/lib/postgresql/data` | postgres |
| `/srv/sentimenter/volumes/redis` | `/data` | redis |
| `/srv/sentimenter/volumes/artifacts` | `/data/artifacts` | api, worker |
| `/srv/sentimenter/volumes/logs` | `/data/logs` | api, worker, daemon |
| `/srv/sentimenter/volumes/grafana_data` | `/var/lib/grafana` | grafana |
| `/srv/sentimenter/volumes/loki_data` | `/loki` | loki |

**Permissions:** Postgres data must be `chown 999:999` and `chmod 700`. Redis dir must be writable by the redis container (e.g. `999:999` or `chmod 700`). **Grafana** runs as UID 472: `chown -R 472:472 /srv/sentimenter/volumes/grafana_data; chmod 700 ...`. **Loki** runs as UID 10001: `chown -R 10001:10001 /srv/sentimenter/volumes/loki_data; chmod 700 ...`. See [6.4 Redis / Postgres won't start](#64-redis--postgres-wont-start) and [6.6 Grafana / Loki restart (permission denied)](#66-grafana--loki-restart-permission-denied).

**Backup:** Back up `/srv/sentimenter/volumes/` (especially `postgres/data` and `redis`). Stop the stack or use `pg_dump` for Postgres if you need consistent backups.

**Local dev** (no production override): compose uses **named** volumes `pgdata`, `redis_data`, `artifacts`, `grafana_data`, `loki_data`.

### 7.1 Cross-check: registry and volumes

| Service | Registry mount | SOURCE_REGISTRY_PATH | Data volumes (prod) |
|---------|----------------|----------------------|----------------------|
| api | `./registry/source_registry.yaml` → `/etc/sentiment_api/source_registry.yaml:ro` | `/etc/sentiment_api/source_registry.yaml` | `/data/artifacts`, `/data/logs` → `/srv/sentimenter/volumes/*` |
| worker | same | same | same |
| daemon | same | same | `/data/logs` only → `/srv/sentimenter/volumes/logs` |

All three compose files (base, production override, frontend_only) mount the registry at the same container path and set the same env var. Production override replaces named volumes with bind mounts under `/srv/sentimenter/volumes/`; base compose uses named volumes for postgres, redis, artifacts, grafana, loki.

---

## 8. Files Reference

| Path | Purpose |
|------|---------|
| `/srv/sentimenter/repo` | Git checkout (root) |
| `/srv/sentimenter/repo/sentiment_api` | Compose dir |
| `/srv/sentimenter/volumes/` | Postgres, Redis, artifacts, logs, grafana, loki (see §7) |
| `/etc/sentimenter/env` | Secrets (DATABASE_URL, REDIS_URL, OPENAI_API_KEY, SENTIMENT_API_API_KEYS) |
| `scripts/deploy/update.sh` | Update script |
| `scripts/deploy/rollback.sh` | Rollback script |
