#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "This script must run as root on the Proxmox host."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

get_default_storage() {
  pvesm status -content rootdir | awk 'NR==2 {print $1}'
}

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

CTID_INPUT="$(prompt "Container ID (blank = next available)" "")"
if [[ -z "${CTID_INPUT}" ]]; then
  CTID="$(pvesh get /cluster/nextid)"
else
  CTID="${CTID_INPUT}"
fi

HOSTNAME="$(prompt "Hostname" "wingman")"

TEMPLATE_DEFAULT="debian-12-standard"
OS_CHOICE="$(prompt "OS template (debian-12-standard, ubuntu-22.04-standard, ubuntu-24.04-standard)" "${TEMPLATE_DEFAULT}")"

STORAGE_DEFAULT="$(get_default_storage)"
STORAGE="$(prompt "Storage" "${STORAGE_DEFAULT}")"

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

TEMPLATE_PATH="$(pveam list ${STORAGE} | awk -v pattern="${OS_CHOICE}" '$2 ~ pattern {print $2}' | tail -n 1)"
if [[ -z "${TEMPLATE_PATH}" ]]; then
  echo "Template ${OS_CHOICE} not found locally. Downloading..."
  pveam update
  pveam download "${STORAGE}" "${OS_CHOICE}"
  TEMPLATE_PATH="$(pveam list ${STORAGE} | awk -v pattern="${OS_CHOICE}" '$2 ~ pattern {print $2}' | tail -n 1)"
fi

if [[ -z "${TEMPLATE_PATH}" ]]; then
  echo "Unable to locate template for ${OS_CHOICE}."
  exit 1
fi

NET0="name=eth0,bridge=${BRIDGE},ip=${IP_CONFIG}"
if [[ -n "${VLAN_TAG}" ]]; then
  NET0+=",tag=${VLAN_TAG}"
fi

ROOTFS="${STORAGE}:${DISK_SIZE}"

pct create "${CTID}" "${STORAGE}:vztmpl/${TEMPLATE_PATH}" \
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

pct exec "${CTID}" -- bash /root/install_inside.sh

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
