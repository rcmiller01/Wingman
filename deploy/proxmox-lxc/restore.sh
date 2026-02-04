#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_dir>"
  exit 1
fi

BACKUP_DIR="$1"
COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"

if [[ ! -f "${BACKUP_DIR}/postgres.sql" ]]; then
  echo "Missing ${BACKUP_DIR}/postgres.sql"
  exit 1
fi

if [[ ! -f "${BACKUP_DIR}/qdrant_storage.tar.gz" ]]; then
  echo "Missing ${BACKUP_DIR}/qdrant_storage.tar.gz"
  exit 1
fi

echo "==> Restoring Postgres from ${BACKUP_DIR}/postgres.sql"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U copilot -d homelab_copilot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U copilot -d homelab_copilot < "${BACKUP_DIR}/postgres.sql"

echo "==> Restoring Qdrant storage from ${BACKUP_DIR}/qdrant_storage.tar.gz"
docker compose -f "${COMPOSE_FILE}" stop qdrant
docker compose -f "${COMPOSE_FILE}" run --rm -T --entrypoint sh qdrant \
  -c "rm -rf /qdrant/storage/* && tar -xzf - -C /" < "${BACKUP_DIR}/qdrant_storage.tar.gz"
docker compose -f "${COMPOSE_FILE}" start qdrant

echo "==> Restore complete"
