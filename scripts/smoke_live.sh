#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"

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
data = json.loads(sys.stdin.read())
print(data["id"])
PY
<<< "${create_response}")"

echo "==> Executing skill ${execution_id}"
execute_response="$(curl "${curl_args[@]}" -X POST "${API_URL}/api/executions/${execution_id}/execute")"

execution_status="$(python - <<'PY'
import json
import sys
data = json.loads(sys.stdin.read())
print(data.get("status", ""))
PY
<<< "${execute_response}")"

if [[ "${execution_status}" != "completed" ]]; then
  echo "Execution did not complete successfully. Status: ${execution_status}"
  exit 1
fi

echo "==> Verifying audit chain"
if [[ -z "${DATABASE_URL:-}" && -n "${POSTGRES_PASSWORD:-}" ]]; then
  export DATABASE_URL="postgresql+asyncpg://copilot:${POSTGRES_PASSWORD}@localhost:5432/homelab_copilot"
fi

python scripts/verify_audit_chain.py

echo "==> Smoke test completed successfully"
