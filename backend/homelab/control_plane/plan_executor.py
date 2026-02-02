"""Plan Executor - Safely executes approved actions."""

import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus
from homelab.adapters.docker_adapter import docker_adapter
from homelab.adapters.proxmox_adapter import proxmox_adapter

class PlanExecutor:
    """Executes actions and updates history."""
    
    async def execute_action(self, db: AsyncSession, action_id: str):
        """Execute a single approved action."""
        
        # 1. Fetch Action
        result = await db.execute(select(ActionHistory).where(ActionHistory.id == action_id))
        action = result.scalar_one_or_none()
        if not action or action.status != ActionStatus.approved:
            print(f"[PlanExecutor] Cannot execute {action_id}: invalid status {action.status}")
            return False
            
        print(f"[PlanExecutor] Executing {action.action_template} on {action.target_resource}")
        
        # 2. Update status to executing
        action.status = ActionStatus.executing
        action.executed_at = datetime.utcnow()
        await db.commit()
        
        success = False
        error = None
        result_data = None
        
        try:
            # 3. Dispatch to specific handler based on template
            if action.action_template == ActionTemplate.restart_resource:
                success, result_data, error = await self._restart_resource(action)
            elif action.action_template == ActionTemplate.start_resource:
                success, result_data, error = await self._start_resource(action)
            elif action.action_template == ActionTemplate.stop_resource:
                success, result_data, error = await self._stop_resource(action)
            else:
                error = f"Unsupported action template: {action.action_template}"
                
        except Exception as e:
            error = f"Execution error: {str(e)}"
            import traceback
            traceback.print_exc()

        # 4. Update Final Status
        action.status = ActionStatus.completed if success else ActionStatus.failed
        action.completed_at = datetime.utcnow()
        action.result = result_data or {}
        action.error = error
        await db.commit()
        
        return success

    async def _restart_resource(self, action: ActionHistory) -> tuple[bool, dict | None, str | None]:
        """Specific handler for restart_resource action."""
        target = action.target_resource
        
        if target.startswith("docker://"):
            container_id = target.split("://")[-1]
            try:
                # Use longer timeout for operations
                timeout = action.parameters.get("timeout", 10)
                await docker_adapter.restart_container(container_id, timeout=timeout)
                return True, {"message": f"Container {container_id} restarted"}, None
            except Exception as e:
                return False, None, str(e)

        elif "proxmox://" in target:
            # Parse proxmox resource ref
            # proxmox://pve/lxc/100
            parts = target.split("://")[-1].split("/")
            node = parts[0]
            type_str = parts[1]
            vmid = int(parts[2])
            
            try:
                await proxmox_adapter.reboot_resource(node, type_str, vmid)
                return True, {"message": f"Reboot sent to {type_str} {vmid} on {node}"}, None
            except Exception as e:
                return False, None, str(e)
                
        return False, None, f"Restart not supported for {target}"

    async def _start_resource(self, action: ActionHistory) -> tuple[bool, dict | None, str | None]:
        """Start a resource."""
        target = action.target_resource
        if target.startswith("docker://"):
            container_id = target.split("://")[-1]
            try:
                await docker_adapter.start_container(container_id)
                return True, {"message": f"Container {container_id} started"}, None
            except Exception as e:
                return False, None, str(e)
        return False, None, f"Start not supported for {target}"

    async def _stop_resource(self, action: ActionHistory) -> tuple[bool, dict | None, str | None]:
        """Stop a resource."""
        target = action.target_resource
        if target.startswith("docker://"):
            container_id = target.split("://")[-1]
            try:
                await docker_adapter.stop_container(container_id)
                return True, {"message": f"Container {container_id} stopped"}, None
            except Exception as e:
                return False, None, str(e)
        return False, None, f"Stop not supported for {target}"

# Singleton
plan_executor = PlanExecutor()
