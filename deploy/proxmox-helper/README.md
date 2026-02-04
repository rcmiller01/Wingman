# Wingman Proxmox Helper

This helper script provisions a dedicated **privileged** LXC container with Docker-in-LXC support and installs the full Wingman stack inside it.

## Quick start

1. On your Proxmox host, run:
   ```bash
   cd /path/to/Wingman
   chmod +x deploy/proxmox-helper/wingman-lxc.sh
   sudo deploy/proxmox-helper/wingman-lxc.sh
   ```
2. Answer the prompts (defaults are safe-by-default).
3. When the script finishes, open the UI URL it prints.

## Why privileged + nesting + keyctl?

Docker-in-LXC needs a privileged container plus `nesting=1` and `keyctl=1` to allow containerized processes and key management inside the LXC. These settings follow common Proxmox guidance for running Docker reliably in an LXC.

## Rollback / uninstall

- Stop and remove the container:
  ```bash
  pct stop <CTID>
  pct destroy <CTID>
  ```
- If you created backups in the container, they live under `/opt/wingman/backups` inside that LXC.

## Notes

- The helper pushes the in-container installer and deploy scripts, then runs the installer.
- The stack is configured with safe-by-default settings: cloud LLM access disabled and LAB mode fail-closed unless explicitly enabled.
