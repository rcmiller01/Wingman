#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"

cd "${COMPOSE_DIR}"

echo "==> Pulling base images"
docker compose -f "${COMPOSE_FILE}" pull postgres qdrant

echo "==> Rebuilding and restarting"
docker compose -f "${COMPOSE_FILE}" up -d --build

echo "==> Update complete"
