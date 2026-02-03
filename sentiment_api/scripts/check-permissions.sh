#!/bin/sh
# sentiment_api — Check volume and file permissions
# Verifies all volumes and key files have correct ownership and permissions.
# Usage: sudo ./check-permissions.sh [--fix]
#   --fix   Attempt to fix incorrect permissions (requires root)
# POSIX-compatible; uses stat (Linux/BSD).

set -e

SERVICE=sentimenter
USER=$SERVICE
HOME_DIR="/srv/${SERVICE}"
VOLUMES_DIR="${HOME_DIR}/volumes"
ENV_FILE="/etc/${SERVICE}/env"
POSTGRES_UID=999
GRAFANA_UID=472
LOKI_UID=10001

FIX=false
[ "${1:-}" = "--fix" ] && FIX=true

ERRORS=0
WARNINGS=0

report() {
  kind=$1
  msg=$2
  echo "[$kind] $msg"
  if [ "$kind" = "ERROR" ]; then
    ERRORS=$((ERRORS + 1))
  else
    WARNINGS=$((WARNINGS + 1))
  fi
}

_stat_owner() {
  path=$1
  stat -c "%u:%g" "$path" 2>/dev/null || stat -f "%u:%g" "$path" 2>/dev/null
}
_stat_mode() {
  path=$1
  stat -c "%a" "$path" 2>/dev/null || stat -f "%OLp" "$path" 2>/dev/null || echo ""
}

check_dir() {
  path=$1
  expected_owner=$2
  expected_mode=$3
  desc=${4:-$path}

  if [ ! -d "$path" ]; then
    report "WARN" "$desc: directory does not exist"
    return
  fi

  owner=$(_stat_owner "$path")
  mode=$(_stat_mode "$path")

  case "$expected_owner" in
    postgres) expected_uid=$POSTGRES_UID; expected_gid=$POSTGRES_UID ;;
    grafana)  expected_uid=$GRAFANA_UID;  expected_gid=$GRAFANA_UID ;;
    loki)     expected_uid=$LOKI_UID;     expected_gid=$LOKI_UID ;;
    *)
      expected_uid=$USER; expected_gid=$USER
      if getent passwd "$USER" >/dev/null 2>&1; then
        expected_uid=$(id -u "$USER" 2>/dev/null || echo "$USER")
        expected_gid=$(id -g "$USER" 2>/dev/null || echo "$USER")
      fi
      ;;
  esac

  current_uid=$(echo "$owner" | cut -d: -f1)
  current_gid=$(echo "$owner" | cut -d: -f2)

  if [ "$current_uid" != "$expected_uid" ] || [ "$current_gid" != "$expected_gid" ]; then
    report "ERROR" "$desc: owner $owner (expected $expected_uid:$expected_gid)"
    if $FIX && [ -n "$expected_uid" ]; then
      chown -R "$expected_uid:$expected_gid" "$path" 2>/dev/null && echo "    Fixed ownership" || report "ERROR" "    Fix failed"
    fi
  fi

  if [ -n "$expected_mode" ] && [ "$mode" != "$expected_mode" ]; then
    report "ERROR" "$desc: mode $mode (expected $expected_mode)"
    if $FIX; then
      chmod -R "$expected_mode" "$path" 2>/dev/null && echo "    Fixed mode" || report "ERROR" "    Fix failed"
    fi
  fi
}

check_file() {
  path=$1
  expected_mode=${2:-600}
  desc=${3:-$path}

  if [ ! -f "$path" ]; then
    report "WARN" "$desc: file does not exist"
    return
  fi

  mode=$(_stat_mode "$path")
  if [ "$mode" != "$expected_mode" ]; then
    report "ERROR" "$desc: mode $mode (expected $expected_mode)"
    if $FIX; then
      chmod "$expected_mode" "$path" 2>/dev/null && echo "    Fixed mode" || report "ERROR" "    Fix failed"
    fi
  fi
}

echo "[*] Checking sentiment_api permissions..."
echo ""

if [ ! -d "$HOME_DIR" ]; then
  report "WARN" "Home dir $HOME_DIR does not exist (not installed?)"
else
  check_dir "$HOME_DIR" "sentimenter" "" "HOME_DIR $HOME_DIR"
  check_dir "$VOLUMES_DIR" "sentimenter" "" "VOLUMES_DIR $VOLUMES_DIR"
fi

check_dir "${VOLUMES_DIR}/postgres/data" "postgres" "700" "postgres/data"
check_dir "${VOLUMES_DIR}/redis" "sentimenter" "" "redis"
check_dir "${VOLUMES_DIR}/weaviate" "sentimenter" "" "weaviate"
check_dir "${VOLUMES_DIR}/artifacts" "sentimenter" "755" "artifacts"
# Ensure universe CSV files in artifacts are readable (644)
for f in sp500.csv nasdaq100.csv sectors.csv industries.csv; do
  p="${VOLUMES_DIR}/artifacts/$f"
  if [ -f "$p" ]; then
    check_file "$p" "644" "artifacts/$f"
  fi
done
check_dir "${VOLUMES_DIR}/logs" "sentimenter" "" "logs"
check_dir "${VOLUMES_DIR}/reports" "sentimenter" "" "reports"
check_dir "${VOLUMES_DIR}/embedding_cache" "sentimenter" "" "embedding_cache"
check_dir "${VOLUMES_DIR}/grafana_data" "grafana" "700" "grafana_data"
check_dir "${VOLUMES_DIR}/loki_data" "loki" "700" "loki_data"

check_file "$ENV_FILE" "600" "ENV_FILE $ENV_FILE"
if [ -f "$ENV_FILE" ]; then
  env_owner=$(_stat_owner "$ENV_FILE")
  if getent passwd "$USER" >/dev/null 2>&1; then
    uid=$(id -u "$USER")
    if [ "$(echo "$env_owner" | cut -d: -f1)" != "$uid" ]; then
      report "ERROR" "ENV_FILE $ENV_FILE: should be owned by $USER"
      if $FIX; then
        chown "$USER:$USER" "$ENV_FILE" 2>/dev/null && echo "    Fixed ownership" || report "ERROR" "    Fix failed"
      fi
    fi
  fi
fi

if [ -d "$VOLUMES_DIR" ]; then
  find "$VOLUMES_DIR" -type d 2>/dev/null | while read -r d; do
    [ -z "$d" ] && continue
    m=$(_stat_mode "$d")
    case "$m" in
      *2|*6) report "WARN" "World-writable: $d (mode $m)" ;;
    esac
  done
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "[!] $ERRORS error(s) found."
  if ! $FIX; then
    echo "    Run with --fix to attempt repairs (requires root)"
  fi
  exit 1
fi
if [ "$WARNINGS" -gt 0 ]; then
  echo "[*] $WARNINGS warning(s). No errors."
  exit 0
fi
echo "[+] All permission checks passed."
