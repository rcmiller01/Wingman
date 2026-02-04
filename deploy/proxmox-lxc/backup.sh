#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="/opt/wingman/backups"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

echo "==> Backing up Postgres to ${BACKUP_DIR}/postgres.sql"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U copilot -d homelab_copilot > "${BACKUP_DIR}/postgres.sql"

echo "==> Backing up Qdrant storage to ${BACKUP_DIR}/qdrant_storage.tar.gz"
docker compose -f "${COMPOSE_FILE}" exec -T qdrant \
  sh -c "tar -czf - /qdrant/storage" > "${BACKUP_DIR}/qdrant_storage.tar.gz"

echo "==> Capturing audit chain verification"
docker compose -f "${COMPOSE_FILE}" exec -T backend \
  python scripts/verify_audit_chain.py > "${BACKUP_DIR}/audit_chain.txt" || true

echo "==> Backup complete: ${BACKUP_DIR}"
