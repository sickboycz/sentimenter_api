# sentiment_api — Update on One Server

**Purpose:** Step-by-step manual to update the sentiment_api deployment on a single server.  
**User:** `sentimenter` | **Data:** `/srv/sentimenter/volumes/` | **Repo:** `/srv/sentimenter/repo`

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

| Symptom | Action |
|---------|--------|
| `Registry file not found` | Ensure `registry/source_registry.yaml` exists in repo; docker-compose sets `SOURCE_REGISTRY_PATH=/etc/sentiment_api/source_registry.yaml` |
| Worker/daemon crash loop | Check logs: `docker logs sentiment_api-worker-1`; verify Postgres + Redis healthy |
| `git pull` fails | Check SSH key / auth; `sudo -u sentimenter git status` |
| Build fails | `docker compose build --no-cache`; check Dockerfile, pyproject.toml |
| Port conflict | Stop other stacks: `docker compose down` (from other compose dirs) |

---

## 7. Files Reference

| Path | Purpose |
|------|---------|
| `/srv/sentimenter/repo` | Git checkout (root) |
| `/srv/sentimenter/repo/sentiment_api` | Compose dir |
| `/srv/sentimenter/volumes/` | Postgres, Redis, artifacts, logs |
| `/etc/sentimenter/env` | Secrets (DATABASE_URL, REDIS_URL, OPENAI_API_KEY, SENTIMENT_API_API_KEYS) |
| `scripts/deploy/update.sh` | Update script |
| `scripts/deploy/rollback.sh` | Rollback script |
