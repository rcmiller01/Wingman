#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="/opt/wingman/deploy"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"
ENV_FILE="${COMPOSE_DIR}/.env"
API_URL="http://localhost:8000"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  if [[ -n "${PUBLIC_API_URL:-}" ]]; then
    API_URL="${PUBLIC_API_URL}"
  fi
fi

API_KEY_FILE="${COMPOSE_DIR}/secrets/wingman_auth_secret"
API_KEY=""
if [[ -f "${API_KEY_FILE}" ]]; then
  API_KEY="$(cat "${API_KEY_FILE}")"
fi

curl_args=("--fail" "--silent" "--show-error")
if [[ -n "${API_KEY}" ]]; then
  curl_args+=("-H" "X-API-Key: ${API_KEY}")
fi

echo "==> Checking health endpoint"
curl "${curl_args[@]}" "${API_URL}/api/health" > /dev/null

echo "==> Creating Tier 1 health skill execution"
create_payload='{"skill_id":"health-docker-ping","parameters":{},"skip_approval":true}'
create_response="$(curl "${curl_args[@]}" -H "Content-Type: application/json" \
  -X POST "${API_URL}/api/executions" -d "${create_payload}")"

execution_id="$(python - <<'PY'
import json
import sys
print(json.loads(sys.stdin.read())["id"])
PY
<<< "${create_response}")"

echo "==> Executing skill ${execution_id}"
execute_response="$(curl "${curl_args[@]}" -X POST "${API_URL}/api/executions/${execution_id}/execute")"

execution_status="$(python - <<'PY'
import json
import sys
print(json.loads(sys.stdin.read()).get("status", ""))
PY
<<< "${execute_response}")"

if [[ "${execution_status}" != "completed" ]]; then
  echo "Execution did not complete successfully. Status: ${execution_status}"
  exit 1
fi

echo "==> Verifying audit chain"
docker compose -f "${COMPOSE_FILE}" exec -T backend python scripts/verify_audit_chain.py

echo "==> Smoke test completed successfully"
