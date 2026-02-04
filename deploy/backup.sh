#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.yml}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-deploy/backups/${TIMESTAMP}}"

mkdir -p "${BACKUP_DIR}"

echo "==> Backing up Postgres to ${BACKUP_DIR}/postgres.sql"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U copilot -d homelab_copilot > "${BACKUP_DIR}/postgres.sql"

echo "==> Backing up Qdrant storage to ${BACKUP_DIR}/qdrant_storage.tar.gz"
docker compose -f "${COMPOSE_FILE}" exec -T qdrant \
  sh -c "tar -czf - /qdrant/storage" > "${BACKUP_DIR}/qdrant_storage.tar.gz"

echo "==> Backup complete: ${BACKUP_DIR}"
