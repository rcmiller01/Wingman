"""Plan Validator - Validates proposed actions."""

from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus
from homelab.adapters.docker_adapter import docker_adapter
from homelab.adapters.proxmox_adapter import proxmox_adapter

class PlanValidator:
    """Validates if plans are safe and executable."""
    
    async def validate_action(self, db: AsyncSession, action_id: str) -> Tuple[bool, str | None]:
        """Validate a single action proposal. Returns (is_valid, reason)."""
        
        # 1. Fetch Action
        result = await db.execute(select(ActionHistory).where(ActionHistory.id == action_id))
        action = result.scalar_one_or_none()
        if not action:
            return False, "Action ID not found"
            
        # 2. Check target resource existence
        target = action.target_resource
        
        if target.startswith("docker://"):
            container_id = target.split("://")[-1]
            container = await docker_adapter.get_container(container_id)
            if not container:
                return False, f"Docker container {container_id} not found"
                
        elif target.startswith("proxmox://"):
            # Check node -> vm/lxc format
            try:
                parts = target.split("/")
                node = parts[2]
                rest = "/".join(parts[3:])
                if "qemu" in rest or "lxc" in rest:
                    # Valid format
                    pass
                else:
                    # Maybe just a node?
                    pass
            except Exception:
                return False, f"Invalid Proxmox resource ref: {target}"
        
        else:
            return False, f"Unsupported resource type: {target}"

        # 3. Check Action Validity for Resource Type
        if action.action_template == ActionTemplate.restart_resource:
            if not (target.startswith("docker://") or target.startswith("proxmox://") or "qemu" in target or "lxc" in target):
                 return False, f"Restart not supported for {target}"

        return True, None

# Singleton
plan_validator = PlanValidator()
