#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"

cd "${COMPOSE_DIR}"

echo "==> Pulling latest images"
docker compose -f "${COMPOSE_FILE}" pull

echo "==> Applying migrations and restarting"
docker compose -f "${COMPOSE_FILE}" up -d

echo "==> Update complete"
