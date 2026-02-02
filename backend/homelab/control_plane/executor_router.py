"""Executor Router - routes plan steps to the appropriate adapters."""

from typing import Any
from homelab.adapters import docker_adapter, proxmox_adapter
from homelab.control_plane.plan_proposal import PlanStep, ActionType

class ExecutorRouter:
    """Routes execution commands to specific infrastructure adapters."""
    
    async def execute_step(self, step: PlanStep) -> dict[str, Any]:
        """Route a single plan step to the correct adapter."""
        action = step.action
        target = step.target
        
        try:
            if action == ActionType.restart_container:
                return await self._handle_docker_restart(target)
            elif action in [ActionType.restart_vm, ActionType.restart_lxc]:
                return await self._handle_proxmox_restart(target)
            else:
                return {"success": False, "error": f"Unsupported action type: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_docker_restart(self, target: str) -> dict[str, Any]:
        """Handle Docker container restart."""
        # target format: docker://container_name_or_id
        container_id = target.replace("docker://", "")
        success = await docker_adapter.restart_container(container_id)
        return {"success": success, "adapter": "docker"}

    async def _handle_proxmox_restart(self, target: str) -> dict[str, Any]:
        """Handle Proxmox resource restart."""
        # target format: proxmox://node/type/id
        parts = target.replace("proxmox://", "").split("/")
        if len(parts) < 3:
            return {"success": False, "error": f"Invalid Proxmox target: {target}"}
            
        node, res_type, res_id = parts[0], parts[1], parts[2]
        
        if res_type == "qemu":
            # VM restart
            await proxmox_adapter.api.nodes(node).qemu(res_id).status.reboot.post()
            return {"success": True, "adapter": "proxmox", "type": "vm"}
        elif res_type == "lxc":
            # LXC restart
            await proxmox_adapter.api.nodes(node).lxc(res_id).status.reboot.post()
            return {"success": True, "adapter": "proxmox", "type": "lxc"}
        
        return {"success": False, "error": f"Unknown Proxmox resource type: {res_type}"}

# Singleton
executor_router = ExecutorRouter()
