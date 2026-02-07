#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "This script must run as root on the Proxmox host."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

KNOWLEDGE_TAR="$(mktemp /tmp/wingman-knowledge.tar.gz.XXXXXX)"
trap 'rm -f "${KNOWLEDGE_TAR}"' EXIT

NONINTERACTIVE="${NONINTERACTIVE:-0}"
export NONINTERACTIVE

get_default_rootfs_storage() {
  pvesm status -content rootdir | awk 'NR>1 {print $1}' | head -n 1
}

get_default_template_storage() {
  pvesm status -content vztmpl | awk 'NR>1 {print $1}' | head -n 1
}

prompt() {
  local text="$1"
  local default="$2"
  if [[ "${NONINTERACTIVE}" == "1" ]]; then
    echo "${default}"
    return
  fi
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
  if [[ "${NONINTERACTIVE}" == "1" ]]; then
    case "${default}" in
      y|Y|yes|YES) echo "yes" ;;
      *) echo "no" ;;
    esac
    return
  fi
  local reply
  read -r -p "${text} [${default}]: " reply
  reply="${reply:-${default}}"
  case "${reply}" in
    y|Y|yes|YES) echo "yes" ;;
    *) echo "no" ;;
  esac
}

CTID_INPUT="${LXC_CTID:-$(prompt "Container ID (blank = next available)" "")}"
if [[ -z "${CTID_INPUT}" ]]; then
  CTID="$(pvesh get /cluster/nextid)"
else
  CTID="${CTID_INPUT}"
fi

HOSTNAME="$(prompt "Hostname" "wingman")"

TEMPLATE_DEFAULT="debian-12-standard"
OS_CHOICE="$(prompt "OS template (debian-12-standard, ubuntu-22.04-standard, ubuntu-24.04-standard)" "${TEMPLATE_DEFAULT}")"

ROOTFS_STORAGE_DEFAULT="$(get_default_rootfs_storage)"
ROOTFS_STORAGE="$(prompt "Rootfs storage" "${ROOTFS_STORAGE_DEFAULT}")"

TMPL_STORAGE_DEFAULT="$(get_default_template_storage)"
TMPL_STORAGE="$(prompt "Template storage" "${TMPL_STORAGE_DEFAULT}")"

DISK_SIZE="$(prompt "Disk size" "20G")"
RAM="$(prompt "RAM (MiB)" "4096")"
CORES="$(prompt "CPU cores" "2")"
BRIDGE="$(prompt "Bridge" "vmbr0")"
VLAN_TAG="$(prompt "VLAN tag (blank for none)" "")"

USE_DHCP="$(prompt_yes_no "Use DHCP?" "Y")"
IP_CONFIG="dhcp"
if [[ "${USE_DHCP}" == "no" ]]; then
  IP_ADDR="$(prompt "Static IP (CIDR, e.g. 192.168.1.50/24)" "")"
  GW_ADDR="$(prompt "Gateway" "")"
  IP_CONFIG="ip=${IP_ADDR},gw=${GW_ADDR}"
fi

ENABLE_FUSE="$(prompt_yes_no "Enable fuse feature?" "N")"
ON_BOOT="$(prompt_yes_no "Start container on boot?" "Y")"

FEATURES="nesting=1,keyctl=1"
if [[ "${ENABLE_FUSE}" == "yes" ]]; then
  FEATURES+=";fuse=1"
fi

# Check if template is already downloaded (pveam list output: storage:volid)
TEMPLATE_VOLID="$(pveam list "${TMPL_STORAGE}" 2>/dev/null | awk -v p="${OS_CHOICE}" '$0 ~ p {print $1}' | tail -n 1)"

if [[ -z "${TEMPLATE_VOLID}" ]]; then
  echo "Template ${OS_CHOICE} not found locally. Downloading..."
  pveam update
  # Resolve the full template filename from the available list
  TMPL_FILENAME="$(pveam available --section system | awk -v p="${OS_CHOICE}" '$2 ~ p {print $2}' | tail -n 1)"
  if [[ -z "${TMPL_FILENAME}" ]]; then
    echo "Unable to find template matching ${OS_CHOICE} in available templates."
    exit 1
  fi
  pveam download "${TMPL_STORAGE}" "${TMPL_FILENAME}"
  TEMPLATE_VOLID="$(pveam list "${TMPL_STORAGE}" 2>/dev/null | awk -v p="${OS_CHOICE}" '$0 ~ p {print $1}' | tail -n 1)"
fi

if [[ -z "${TEMPLATE_VOLID}" ]]; then
  echo "Unable to locate template for ${OS_CHOICE} after download."
  exit 1
fi

NET0="name=eth0,bridge=${BRIDGE},ip=${IP_CONFIG}"
if [[ -n "${VLAN_TAG}" ]]; then
  NET0+=",tag=${VLAN_TAG}"
fi

ROOTFS="${ROOTFS_STORAGE}:${DISK_SIZE}"

pct create "${CTID}" "${TEMPLATE_VOLID}" \
  --hostname "${HOSTNAME}" \
  --cores "${CORES}" \
  --memory "${RAM}" \
  --net0 "${NET0}" \
  --rootfs "${ROOTFS}" \
  --features "${FEATURES}" \
  --unprivileged 0 \
  --onboot $( [[ "${ON_BOOT}" == "yes" ]] && echo 1 || echo 0 )

pct start "${CTID}"

echo "Waiting for container network..."
for _ in {1..30}; do
  if pct exec "${CTID}" -- bash -c "ip -4 addr show dev eth0 | grep -q 'inet '"; then
    break
  fi
  sleep 2
done

pct exec "${CTID}" -- bash -c "apt-get update -y" >/dev/null

pct push "${CTID}" "${REPO_ROOT}/deploy/proxmox-lxc/install_inside.sh" /root/install_inside.sh
pct push "${CTID}" "${REPO_ROOT}/deploy/docker-compose.yml" /root/wingman-compose.yml
pct push "${CTID}" "${REPO_ROOT}/deploy/proxmox-lxc/update.sh" /root/update.sh
pct push "${CTID}" "${REPO_ROOT}/deploy/proxmox-lxc/backup.sh" /root/backup.sh
pct push "${CTID}" "${REPO_ROOT}/deploy/proxmox-lxc/restore.sh" /root/restore.sh
pct push "${CTID}" "${REPO_ROOT}/deploy/proxmox-lxc/smoke.sh" /root/smoke.sh

if [[ -d "${REPO_ROOT}/knowledge" ]]; then
  tar -C "${REPO_ROOT}" -czf "${KNOWLEDGE_TAR}" knowledge
  pct push "${CTID}" "${KNOWLEDGE_TAR}" /root/knowledge.tgz
  pct exec "${CTID}" -- bash -c "mkdir -p /opt/wingman/knowledge && tar -xzf /root/knowledge.tgz -C /opt/wingman"
else
  echo "Warning: knowledge directory not found; skipping knowledge copy."
fi

# Forward env vars for non-interactive mode
INNER_ENV=""
for var in NONINTERACTIVE WINGMAN_EXECUTION_MODE WINGMAN_ALLOW_CLOUD_LLM \
           WINGMAN_PROXMOX_URL WINGMAN_PROXMOX_VERIFY_SSL WINGMAN_DOCKER_HOST \
           WINGMAN_TIMEZONE WINGMAN_BASE_URL WINGMAN_AUTH_SECRET \
           WINGMAN_AUTH_METHOD WINGMAN_PROXMOX_USER WINGMAN_PROXMOX_TOKEN_NAME \
           WINGMAN_PROXMOX_TOKEN WINGMAN_PROXMOX_PASSWORD; do
  if [[ -n "${!var:-}" ]]; then
    INNER_ENV+="${var}=${!var} "
  fi
done

pct exec "${CTID}" -- bash -c "${INNER_ENV} bash /root/install_inside.sh"

CONTAINER_IP="$(pct exec "${CTID}" -- bash -c "ip -4 -o addr show dev eth0 | awk '{print \$4}' | cut -d/ -f1")"

echo ""
cat <<EOF
============================================================
Wingman appliance is ready
CTID: ${CTID}
IP: ${CONTAINER_IP}

UI:     http://${CONTAINER_IP}:3000
API:    http://${CONTAINER_IP}:8000
Health: http://${CONTAINER_IP}:8000/api/health/ready

Update:  pct exec ${CTID} -- bash /root/update.sh
Backup:  pct exec ${CTID} -- bash /root/backup.sh
Restore: pct exec ${CTID} -- bash /root/restore.sh /opt/wingman/backups/<timestamp>
Wipe:    pct stop ${CTID} && pct destroy ${CTID}
============================================================
EOF
