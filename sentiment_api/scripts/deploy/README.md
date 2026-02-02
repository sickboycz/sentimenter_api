# sentiment_api deployment scripts

Production deployment following **Generic Service Installation and Update Manual v2**.

**User:** `sentimenter`  
**Data:** `/srv/sentimenter/volumes/` (out-of-Docker)

## Scripts

| Script | Purpose |
|--------|---------|
| `install.sh` | First-time install (user, dirs, build, start, DB init) |
| `create-service.sh` | Create systemd unit only (e.g. after install failed before step 7) |
| `verify-repo.sh` | Check required files after pull; optional `--pull` to fetch and pull |
| `update.sh` | Safe update (git pull, rebuild, restart) |
| `rollback.sh` | Rollback to previous commit |

## Usage

```bash
# First install (repo must be cloned to /srv/sentimenter/repo)
sudo ./install.sh

# Re-run install (user/dirs exist)
sudo ./install.sh --skip-user

# Create service only (install failed before systemd unit was created)
sudo ./create-service.sh --enable
# or: sudo ./install.sh --service-only

# Verify repo after pull (required files present)
sudo ./verify-repo.sh
sudo ./verify-repo.sh --pull   # fetch + pull then check

# Update (repo already cloned)
sudo ./update.sh

# Rollback
sudo ./rollback.sh
```

## Fresh deploy (prune + pull + rebuild)

When the stack has changed (e.g. new Weaviate + embedding cache) and you want a clean rebuild **without** deleting the repo or volume data:

1. **Stop and prune** (from server):
   ```bash
   cd /srv/sentimenter/repo/sentiment_api
   docker compose -f docker-compose.yml -f docker-compose.production.yml --env-file /etc/sentimenter/env down
   docker container prune -f
   docker image prune -f
   ```
2. **Create new volume dirs** (if not present):
   ```bash
   sudo mkdir -p /srv/sentimenter/volumes/weaviate /srv/sentimenter/volumes/embedding_cache
   sudo chown -R sentimenter:sentimenter /srv/sentimenter/volumes/weaviate /srv/sentimenter/volumes/embedding_cache
   ```
3. **Pull and run update**:
   ```bash
   sudo -u sentimenter git pull
   cd /srv/sentimenter/repo/sentiment_api
   sudo ./scripts/deploy/update.sh
   ```

**Do not run full `install.sh`** unless you are setting up a new server; it would recreate user/dirs and re-apply schema. For “fresh rebuild” on an existing server, the sequence above (prune → create new dirs → pull → update) is enough.

## Prerequisites

1. Clone repo: `sudo -u sentimenter git clone https://github.com/sickboycz/sentimenter_api.git /srv/sentimenter/repo`
2. Edit secrets: `/etc/sentimenter/env`
3. Run `./install.sh`

See **docs/INSTALLATION_MANUAL.md** for full procedure.
