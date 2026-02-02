#!/usr/bin/env bash
# sentiment_api — Check volume and file permissions
# Verifies all volumes and key files have correct ownership and permissions.
# Usage: sudo ./check-permissions.sh [--fix]
#   --fix   Attempt to fix incorrect permissions (requires root)
# Note: Uses GNU stat (Linux). On macOS, ownership checks work; mode checks may differ.

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
[[ "${1:-}" == "--fix" ]] && FIX=true

ERRORS=0
WARNINGS=0

report() {
  local kind=$1
  local msg=$2
  if [[ "$kind" == "ERROR" ]]; then
    echo "[$kind] $msg"
    ((ERRORS++)) || true
  else
    echo "[$kind] $msg"
    ((WARNINGS++)) || true
  fi
}

# Portable stat (Linux: stat -c, BSD/macOS: stat -f)
_stat_owner() {
  local path=$1
  stat -c "%u:%g" "$path" 2>/dev/null || stat -f "%u:%g" "$path" 2>/dev/null
}
_stat_mode() {
  local path=$1
  stat -c "%a" "$path" 2>/dev/null || stat -f "%OLp" "$path" 2>/dev/null || echo ""
}

check_dir() {
  local path=$1
  local expected_owner=$2
  local expected_mode=$3
  local desc=${4:-$path}

  if [[ ! -d "$path" ]]; then
    report "WARN" "$desc: directory does not exist"
    return
  fi

  local owner mode
  owner=$(_stat_owner "$path")
  mode=$(_stat_mode "$path")

  local expected_uid expected_gid
  case "$expected_owner" in
    postgres) expected_uid=$POSTGRES_UID; expected_gid=$POSTGRES_UID ;;
    grafana)  expected_uid=$GRAFANA_UID;  expected_gid=$GRAFANA_UID ;;
    loki)     expected_uid=$LOKI_UID;     expected_gid=$LOKI_UID ;;
    *)        expected_uid=$USER; expected_gid=$USER
              if getent passwd "$USER" >/dev/null 2>&1; then
                expected_uid=$(id -u "$USER" 2>/dev/null || echo "$USER")
                expected_gid=$(id -g "$USER" 2>/dev/null || echo "$USER")
              fi
              ;;
  esac

  local current_uid current_gid
  current_uid=$(echo "$owner" | cut -d: -f1)
  current_gid=$(echo "$owner" | cut -d: -f2)

  if [[ "$current_uid" != "$expected_uid" ]] || [[ "$current_gid" != "$expected_gid" ]]; then
    report "ERROR" "$desc: owner $owner (expected $expected_uid:$expected_gid)"
    if $FIX && [[ -n "$expected_uid" ]]; then
      chown -R "$expected_uid:$expected_gid" "$path" 2>/dev/null && echo "    Fixed ownership" || report "ERROR" "    Fix failed"
    fi
  fi

  if [[ -n "$expected_mode" ]] && [[ "$mode" != "$expected_mode" ]]; then
    report "ERROR" "$desc: mode $mode (expected $expected_mode)"
    if $FIX; then
      chmod -R "$expected_mode" "$path" 2>/dev/null && echo "    Fixed mode" || report "ERROR" "    Fix failed"
    fi
  fi
}

check_file() {
  local path=$1
  local expected_mode=${2:-600}
  local desc=${3:-$path}

  if [[ ! -f "$path" ]]; then
    report "WARN" "$desc: file does not exist"
    return
  fi

  local mode
  mode=$(_stat_mode "$path")
  if [[ "$mode" != "$expected_mode" ]]; then
    report "ERROR" "$desc: mode $mode (expected $expected_mode)"
    if $FIX; then
      chmod "$expected_mode" "$path" 2>/dev/null && echo "    Fixed mode" || report "ERROR" "    Fix failed"
    fi
  fi
}

echo "[*] Checking sentiment_api permissions..."
echo ""

# Home and volumes base
if [[ ! -d "$HOME_DIR" ]]; then
  report "WARN" "Home dir $HOME_DIR does not exist (not installed?)"
else
  check_dir "$HOME_DIR" "sentimenter" "" "HOME_DIR $HOME_DIR"
  check_dir "$VOLUMES_DIR" "sentimenter" "" "VOLUMES_DIR $VOLUMES_DIR"
fi

# Volume subdirs (production layout)
check_dir "${VOLUMES_DIR}/postgres/data" "postgres" "700" "postgres/data"
check_dir "${VOLUMES_DIR}/redis" "sentimenter" "" "redis"
check_dir "${VOLUMES_DIR}/weaviate" "sentimenter" "" "weaviate"
check_dir "${VOLUMES_DIR}/artifacts" "sentimenter" "" "artifacts"
check_dir "${VOLUMES_DIR}/logs" "sentimenter" "" "logs"
check_dir "${VOLUMES_DIR}/reports" "sentimenter" "" "reports"
check_dir "${VOLUMES_DIR}/embedding_cache" "sentimenter" "" "embedding_cache"
check_dir "${VOLUMES_DIR}/grafana_data" "grafana" "700" "grafana_data"
check_dir "${VOLUMES_DIR}/loki_data" "loki" "700" "loki_data"

# Env file
check_file "$ENV_FILE" "600" "ENV_FILE $ENV_FILE"
if [[ -f "$ENV_FILE" ]]; then
  env_owner=$(_stat_owner "$ENV_FILE")
  if getent passwd "$USER" >/dev/null 2>&1; then
    uid=$(id -u "$USER")
    if [[ "$(echo "$env_owner" | cut -d: -f1)" != "$uid" ]]; then
      report "ERROR" "ENV_FILE $ENV_FILE: should be owned by $USER"
      if $FIX; then
        chown "$USER:$USER" "$ENV_FILE" 2>/dev/null && echo "    Fixed ownership" || report "ERROR" "    Fix failed"
      fi
    fi
  fi
fi

# Recursive check: ensure no world-writable dirs in volumes
if [[ -d "$VOLUMES_DIR" ]]; then
  while IFS= read -r -d '' d; do
    m=$(_stat_mode "$d")
    if [[ "$m" == *2 ]] || [[ "$m" == *6 ]]; then
      report "WARN" "World-writable: $d (mode $m)"
    fi
  done < <(find "$VOLUMES_DIR" -type d -print0 2>/dev/null || true)
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "[!] $ERRORS error(s) found."
  if ! $FIX; then
    echo "    Run with --fix to attempt repairs (requires root)"
  fi
  exit 1
fi
if [[ $WARNINGS -gt 0 ]]; then
  echo "[*] $WARNINGS warning(s). No errors."
  exit 0
fi
echo "[+] All permission checks passed."
