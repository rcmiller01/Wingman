"""Executor Router - routes plan steps to the appropriate adapters."""

import re
from typing import Any
from homelab.adapters import docker_adapter, proxmox_adapter
from homelab.control_plane.plan_proposal import PlanStep
from homelab.storage.models import ActionTemplate

# Validation patterns
_DOCKER_CONTAINER_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')
_PROXMOX_NODE_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
_PROXMOX_VMID_PATTERN = re.compile(r'^\d+$')


class ExecutorRouter:
    """Routes execution commands to specific infrastructure adapters."""
    
    async def execute_step(self, step: PlanStep) -> dict[str, Any]:
        """Route a single plan step to the correct adapter."""
        action = step.action
        target = step.target
        
        try:
            if action == ActionTemplate.restart_resource:
                if target.startswith("docker://"):
                    return await self._handle_docker_restart(target)
                if target.startswith("proxmox://"):
                    return await self._handle_proxmox_restart(target)
                return {"success": False, "error": f"Unsupported restart target: {target}"}
            return {"success": False, "error": f"Unsupported action type: {action}"}
        except ValueError as e:
            # Input validation errors
            return {"success": False, "error": f"Validation error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_docker_restart(self, target: str) -> dict[str, Any]:
        """Handle Docker container restart with input validation."""
        # target format: docker://container_name_or_id
        container_id = target.replace("docker://", "")
        
        # Validate container ID/name to prevent injection
        if not container_id or not _DOCKER_CONTAINER_PATTERN.match(container_id):
            raise ValueError(f"Invalid Docker container identifier: {container_id}")
        if len(container_id) > 128:
            raise ValueError("Container identifier too long")
        
        success = await docker_adapter.restart_container(container_id)
        return {"success": success, "adapter": "docker"}

    async def _handle_proxmox_restart(self, target: str) -> dict[str, Any]:
        """Handle Proxmox resource restart with strict input validation."""
        # target format: proxmox://node/type/id
        parts = target.replace("proxmox://", "").split("/")
        if len(parts) < 3:
            raise ValueError(f"Invalid Proxmox target format (expected node/type/id): {target}")
        
        node, res_type, res_id_str = parts[0], parts[1], parts[2]
        
        # Validate node name
        if not node or not _PROXMOX_NODE_PATTERN.match(node):
            raise ValueError(f"Invalid Proxmox node name: {node}")
        if len(node) > 64:
            raise ValueError("Node name too long")
        
        # Validate resource type (strict whitelist)
        if res_type not in ("qemu", "lxc"):
            raise ValueError(f"Invalid Proxmox resource type (must be qemu or lxc): {res_type}")
        
        # Validate VMID (must be numeric, no injection possible)
        if not _PROXMOX_VMID_PATTERN.match(res_id_str):
            raise ValueError(f"Invalid Proxmox VMID (must be numeric): {res_id_str}")
        
        try:
            res_id = int(res_id_str)
        except ValueError:
            raise ValueError(f"Invalid Proxmox VMID: {res_id_str}")
        
        if res_id < 100 or res_id > 999999999:
            raise ValueError(f"Proxmox VMID out of valid range (100-999999999): {res_id}")
        
        # Execute via adapter
        success = await proxmox_adapter.reboot_resource(node, res_type, res_id)
        return {"success": success, "adapter": "proxmox", "type": "vm" if res_type == "qemu" else "lxc"}


# Singleton
executor_router = ExecutorRouter()
