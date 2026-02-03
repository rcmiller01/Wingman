#!/usr/bin/env bash
set -euo pipefail

DUMP_FILE=${1:-}

if [[ -z "$DUMP_FILE" ]]; then
  echo "Usage: $0 /path/to/wingman_postgres_YYYYMMDD_HHMMSS.dump"
  exit 1
fi

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "Dump file not found: $DUMP_FILE"
  exit 1
fi

: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=wingman}"
: "${POSTGRES_USER:=postgres}"

export PGPASSWORD=${POSTGRES_PASSWORD:-}

pg_restore \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --clean \
  --if-exists \
  --dbname "$POSTGRES_DB" \
  "$DUMP_FILE"

echo "Restore completed from $DUMP_FILE"
