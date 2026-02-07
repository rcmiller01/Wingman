#!/usr/bin/env bash
# Wingman Quickstart — non-interactive Proxmox LXC deployment.
#
# Usage:
#   1. Copy the entire Wingman repo to the Proxmox host (or clone it).
#   2. Edit the CONFIGURATION section below.
#   3. Run:  bash deploy/proxmox-helper/quickstart.sh
#
# This is a thin wrapper around wingman-lxc.sh and install_inside.sh that
# pre-fills every prompt so the deployment runs unattended.
set -euo pipefail

# ===========================================================================
# CONFIGURATION — edit these for your environment
# ===========================================================================

# LXC settings (leave CTID empty to auto-assign)
export LXC_CTID=""
export LXC_HOSTNAME="wingman"
export LXC_TEMPLATE="debian-12-standard"
export LXC_DISK="20G"
export LXC_RAM="4096"
export LXC_CORES="2"
export LXC_BRIDGE="vmbr0"
# Set for static IP, leave empty for DHCP
export LXC_STATIC_IP=""   # e.g. 192.168.50.200/24
export LXC_GATEWAY=""     # e.g. 192.168.50.1

# Proxmox API connection (from inside the LXC)
export WINGMAN_PROXMOX_URL=""         # e.g. https://192.168.1.100:8006
export WINGMAN_PROXMOX_VERIFY_SSL="false"

# Proxmox credentials — choose "token" or "password"
export WINGMAN_AUTH_METHOD="password"
export WINGMAN_PROXMOX_USER="root@pam"
export WINGMAN_PROXMOX_PASSWORD=""    # fill in your Proxmox password
export WINGMAN_PROXMOX_TOKEN_NAME=""  # or use token auth instead
export WINGMAN_PROXMOX_TOKEN=""

# Docker host — leave empty to use the local socket inside the LXC.
# To monitor Docker on a remote VM, set to tcp://VM_IP:2375
export WINGMAN_DOCKER_HOST=""

# Wingman settings
export WINGMAN_EXECUTION_MODE="integration"
export WINGMAN_ALLOW_CLOUD_LLM="false"
export WINGMAN_TIMEZONE=""
export WINGMAN_BASE_URL=""

# Auth secret — leave empty to auto-generate
export WINGMAN_AUTH_SECRET=""

# ===========================================================================
# END CONFIGURATION — nothing below needs editing
# ===========================================================================

export NONINTERACTIVE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/wingman-lxc.sh"
