#!/usr/bin/env bash
# Initialize sentiment_api Postgres schema.
# Usage: ./scripts/init_db.sh [DATABASE_URL]
# Default: postgresql://sentiment:sentiment@localhost:5432/sentiment

DB_URL="${1:-postgresql://sentiment:sentiment@localhost:5432/sentiment}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCHEMA="$ROOT/Docs/sentiment_api_tech_package_v1.0/db/schema.sql"
if [[ ! -f "$SCHEMA" ]]; then
  echo "Schema not found. Run from sentiment_api or project root."
  exit 1
fi
echo "Applying schema from $SCHEMA to $DB_URL"
psql "$DB_URL" -f "$SCHEMA"
