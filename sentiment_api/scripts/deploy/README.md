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

## Prerequisites

1. Clone repo: `sudo -u sentimenter git clone https://github.com/sickboycz/sentimenter_api.git /srv/sentimenter/repo`
2. Edit secrets: `/etc/sentimenter/env`
3. Run `./install.sh`

See **docs/INSTALLATION_MANUAL.md** for full procedure.
