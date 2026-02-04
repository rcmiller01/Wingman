#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"

cd "${COMPOSE_DIR}"

echo "==> Pulling base images"
docker compose -f "${COMPOSE_FILE}" pull postgres qdrant

echo "==> Rebuilding Wingman services"
docker compose -f "${COMPOSE_FILE}" build backend frontend

echo "==> Applying migrations and restarting"
docker compose -f "${COMPOSE_FILE}" up -d

echo "==> Update complete"
