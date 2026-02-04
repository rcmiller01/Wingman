#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=${1:-./backups}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="wingman_postgres_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

: "${POSTGRES_HOST:=localhost}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=wingman}"
: "${POSTGRES_USER:=postgres}"

export PGPASSWORD=${POSTGRES_PASSWORD:-}

pg_dump \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --format=custom \
  --file "$BACKUP_DIR/$FILENAME" \
  "$POSTGRES_DB"

echo "Backup written to $BACKUP_DIR/$FILENAME"
