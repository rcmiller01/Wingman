#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root inside the container."
  exit 1
fi

prompt() {
  local text="$1"
  local default="$2"
  local value
  if [[ -n "${default}" ]]; then
    read -r -p "${text} [${default}]: " value
    echo "${value:-${default}}"
  else
    read -r -p "${text}: " value
    echo "${value}"
  fi
}

prompt_yes_no() {
  local text="$1"
  local default="$2"
  local reply
  read -r -p "${text} [${default}]: " reply
  reply="${reply:-${default}}"
  case "${reply}" in
    y|Y|yes|YES) echo "yes" ;;
    *) echo "no" ;;
  esac
}

ensure_packages() {
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release openssl
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi

  ensure_packages

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/"${ID}"/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} \
    ${VERSION_CODENAME} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
else
  echo "Unsupported OS."
  exit 1
fi

if [[ "${ID}" != "debian" && "${ID}" != "ubuntu" ]]; then
  echo "Unsupported OS: ${ID}"
  exit 1
fi

install_docker

mkdir -p /opt/wingman/deploy /opt/wingman/data /opt/wingman/knowledge

if [[ -f /root/wingman-compose.yml ]]; then
  cp /root/wingman-compose.yml /opt/wingman/deploy/docker-compose.yml
fi

if [[ -f /root/update.sh ]]; then
  cp /root/update.sh /opt/wingman/deploy/update.sh
  chmod +x /opt/wingman/deploy/update.sh
fi
if [[ -f /root/backup.sh ]]; then
  cp /root/backup.sh /opt/wingman/deploy/backup.sh
  chmod +x /opt/wingman/deploy/backup.sh
fi
if [[ -f /root/restore.sh ]]; then
  cp /root/restore.sh /opt/wingman/deploy/restore.sh
  chmod +x /opt/wingman/deploy/restore.sh
fi
if [[ -f /root/smoke.sh ]]; then
  cp /root/smoke.sh /opt/wingman/deploy/smoke.sh
  chmod +x /opt/wingman/deploy/smoke.sh
fi

if [[ ! -f /opt/wingman/deploy/docker-compose.yml ]]; then
  echo "Missing docker-compose.yml. Ensure the helper script pushed it."
  exit 1
fi

IP_ADDR="$(ip -4 route get 1.1.1.1 | awk '{print $7; exit}')"
PUBLIC_API_URL_DEFAULT="http://${IP_ADDR}:8000"
PUBLIC_UI_URL_DEFAULT="http://${IP_ADDR}:3000"

EXECUTION_MODE="$(prompt "Execution mode (integration or lab)" "integration")"
ALLOW_CLOUD_LLM="$(prompt "Allow cloud LLM?" "false")"
PROXMOX_URL="$(prompt "Proxmox API URL (https://pve:8006)" "")"
PROXMOX_VERIFY_SSL="$(prompt "Verify Proxmox SSL?" "false")"
TIMEZONE="$(prompt "Timezone (optional)" "")"
BASE_URL="$(prompt "Base URL (optional)" "")"
LAB_ENABLE="no"
LAB_ALLOWLIST_CONTAINERS=""
LAB_ALLOWLIST_VMS=""
LAB_ALLOWLIST_NODES=""
ALLOW_DANGEROUS_OPS="false"
READ_ONLY="false"

if [[ "${EXECUTION_MODE}" == "lab" ]]; then
  LAB_ENABLE="yes"
  LAB_ALLOWLIST_CONTAINERS="$(prompt "LAB container allowlist (comma-separated)" "")"
  LAB_ALLOWLIST_VMS="$(prompt "LAB VM allowlist (comma-separated)" "")"
  LAB_ALLOWLIST_NODES="$(prompt "LAB node allowlist (comma-separated)" "")"
  if [[ -z "${LAB_ALLOWLIST_CONTAINERS}" && -z "${LAB_ALLOWLIST_VMS}" && -z "${LAB_ALLOWLIST_NODES}" ]]; then
    echo "LAB mode is enabled but no allowlists were provided. LAB remains fail-closed."
  fi
else
  EXECUTION_MODE="integration"
fi

mkdir -p /run/secrets/wingman
chmod 700 /run/secrets/wingman
mkdir -p /opt/wingman/deploy
if [[ ! -e /opt/wingman/deploy/secrets ]]; then
  ln -s /run/secrets/wingman /opt/wingman/deploy/secrets
fi

SECRETS_DIR="/run/secrets/wingman"
SECRET_FILES=(
  "wingman_auth_secret"
  "proxmox_api_token"
  "proxmox_user"
  "proxmox_password"
  "proxmox_token_name"
)
for secret_file in "${SECRET_FILES[@]}"; do
  touch "${SECRETS_DIR}/${secret_file}"
  chmod 600 "${SECRETS_DIR}/${secret_file}"
done

read -r -s -p "Wingman auth secret (required, will not echo): " WINGMAN_AUTH_SECRET_INPUT
printf "\n"
if [[ -z "${WINGMAN_AUTH_SECRET_INPUT}" ]]; then
  echo "Auth secret is required. Generating one."
  WINGMAN_AUTH_SECRET_INPUT="$(openssl rand -hex 32)"
fi

AUTH_METHOD="$(prompt "Proxmox auth method (token or password)" "token")"
PROXMOX_USER=""
PROXMOX_TOKEN_NAME=""
PROXMOX_PASSWORD=""
PROXMOX_TOKEN=""

if [[ "${AUTH_METHOD}" == "token" ]]; then
  PROXMOX_USER="$(prompt "Proxmox user (e.g. root@pam)" "")"
  PROXMOX_TOKEN_NAME="$(prompt "Proxmox token name" "")"
  read -r -s -p "Proxmox API token (required, will not echo): " PROXMOX_TOKEN
  printf "\n"
  if [[ -z "${PROXMOX_TOKEN}" ]]; then
    echo "Proxmox token is required for token auth."
    exit 1
  fi
else
  PROXMOX_USER="$(prompt "Proxmox user (e.g. root@pam)" "")"
  read -r -s -p "Proxmox password (required, will not echo): " PROXMOX_PASSWORD
  printf "\n"
  if [[ -z "${PROXMOX_PASSWORD}" ]]; then
    echo "Proxmox password is required for password auth."
    exit 1
  fi
fi

POSTGRES_PASSWORD="$(openssl rand -hex 32)"
echo "Generated Postgres password saved in /opt/wingman/deploy/.env."

cat > /opt/wingman/deploy/.env <<ENV
EXECUTION_MODE=${EXECUTION_MODE}
WINGMAN_EXECUTION_MODE=${EXECUTION_MODE}
ALLOW_CLOUD_LLM=${ALLOW_CLOUD_LLM}
PROXMOX_HOST=${PROXMOX_URL}
PROXMOX_VERIFY_SSL=${PROXMOX_VERIFY_SSL}
PUBLIC_API_URL=${PUBLIC_API_URL_DEFAULT}
PUBLIC_UI_URL=${PUBLIC_UI_URL_DEFAULT}
AUTH_ENABLED=true
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
WINGMAN_ALLOW_DANGEROUS_OPS=${ALLOW_DANGEROUS_OPS}
WINGMAN_READ_ONLY=${READ_ONLY}
ENV

if [[ -n "${TIMEZONE}" ]]; then
  echo "TZ=${TIMEZONE}" >> /opt/wingman/deploy/.env
fi
if [[ -n "${BASE_URL}" ]]; then
  echo "BASE_URL=${BASE_URL}" >> /opt/wingman/deploy/.env
fi
if [[ "${LAB_ENABLE}" == "yes" ]]; then
  echo "WINGMAN_CONTAINER_ALLOWLIST=${LAB_ALLOWLIST_CONTAINERS}" >> /opt/wingman/deploy/.env
  echo "WINGMAN_VM_ALLOWLIST=${LAB_ALLOWLIST_VMS}" >> /opt/wingman/deploy/.env
  echo "WINGMAN_NODE_ALLOWLIST=${LAB_ALLOWLIST_NODES}" >> /opt/wingman/deploy/.env
fi
if [[ -n "${PROXMOX_USER}" ]]; then
  echo "PROXMOX_USER=${PROXMOX_USER}" >> /opt/wingman/deploy/.env
fi
if [[ -n "${PROXMOX_TOKEN_NAME}" ]]; then
  echo "PROXMOX_TOKEN_NAME=${PROXMOX_TOKEN_NAME}" >> /opt/wingman/deploy/.env
fi

printf "%s" "${WINGMAN_AUTH_SECRET_INPUT}" > /run/secrets/wingman/wingman_auth_secret
chmod 600 /run/secrets/wingman/wingman_auth_secret

if [[ -n "${PROXMOX_TOKEN}" ]]; then
  printf "%s" "${PROXMOX_TOKEN}" > /run/secrets/wingman/proxmox_api_token
  chmod 600 /run/secrets/wingman/proxmox_api_token
fi
if [[ -n "${PROXMOX_PASSWORD}" ]]; then
  printf "%s" "${PROXMOX_PASSWORD}" > /run/secrets/wingman/proxmox_password
  chmod 600 /run/secrets/wingman/proxmox_password
fi
if [[ -n "${PROXMOX_USER}" ]]; then
  printf "%s" "${PROXMOX_USER}" > /run/secrets/wingman/proxmox_user
  chmod 600 /run/secrets/wingman/proxmox_user
fi
if [[ -n "${PROXMOX_TOKEN_NAME}" ]]; then
  printf "%s" "${PROXMOX_TOKEN_NAME}" > /run/secrets/wingman/proxmox_token_name
  chmod 600 /run/secrets/wingman/proxmox_token_name
fi

cd /opt/wingman/deploy

docker compose --env-file .env up -d --build

echo "Waiting for API health..."
for _ in {1..40}; do
  if curl -fsS http://localhost:8000/api/health/ready >/dev/null; then
    break
  fi
  sleep 5
done

if [[ -x /opt/wingman/deploy/smoke.sh ]]; then
  /opt/wingman/deploy/smoke.sh
fi

echo "DONE"
echo "UI: ${PUBLIC_UI_URL_DEFAULT}"
echo "API: ${PUBLIC_API_URL_DEFAULT}"
echo "Logs: docker compose -f /opt/wingman/deploy/docker-compose.yml logs -f"
echo "Update: /opt/wingman/deploy/update.sh"
echo "Backup: /opt/wingman/deploy/backup.sh"
echo "Restore: /opt/wingman/deploy/restore.sh"
