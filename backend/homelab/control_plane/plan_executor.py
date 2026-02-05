"""Plan Executor - Safely executes approved actions."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.config import get_settings
from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus
from homelab.adapters.proxmox_adapter import proxmox_adapter
from homelab.execution_plugins import PluginAction, execution_registry
from homelab.workers.service import enqueue_worker_task


class PlanExecutor:
    """Executes actions and updates history."""

    async def execute_action(self, db: AsyncSession, action_id: str):
        """Execute a single approved action."""

        result = await db.execute(select(ActionHistory).where(ActionHistory.id == action_id))
        action = result.scalar_one_or_none()
        if not action or action.status != ActionStatus.approved:
            print(f"[PlanExecutor] Cannot execute {action_id}: invalid status {action.status}")
            return False

        settings = get_settings()
        if settings.worker_delegation_enabled and action.target_resource.startswith("docker://"):
            queued = await self._enqueue_worker_execution(db, action)
            return queued

        print(f"[PlanExecutor] Executing {action.action_template} on {action.target_resource}")

        action.status = ActionStatus.executing
        action.executed_at = datetime.utcnow()
        await db.commit()

        success = False
        error = None
        result_data = None

        try:
            success, result_data, error = await self._dispatch_action(action)
        except Exception as e:
            error = f"Execution error: {str(e)}"
            import traceback
            traceback.print_exc()

        action.status = ActionStatus.completed if success else ActionStatus.failed
        action.completed_at = datetime.utcnow()
        action.result = result_data or {}
        action.error = error
        await db.commit()

        return success

    async def _enqueue_worker_execution(self, db: AsyncSession, action: ActionHistory) -> bool:
        action_map = {
            ActionTemplate.restart_resource: "restart",
            ActionTemplate.start_resource: "start",
            ActionTemplate.stop_resource: "stop",
        }
        plugin_action_name = action_map.get(action.action_template)
        if plugin_action_name is None:
            return False

        settings = get_settings()
        action.status = ActionStatus.executing
        action.executed_at = datetime.utcnow()

        payload = {
            "plugin_id": "docker",
            "action": plugin_action_name,
            "target": action.target_resource,
            "params": (action.parameters or {}).get("params", {}),
            "action_id": action.id,
            "todo_id": (action.parameters or {}).get("todo_id"),
        }

        task = await enqueue_worker_task(
            db,
            task_type="execute_action",
            worker_id=settings.worker_default_id,
            idempotency_key=f"{action.id}:1",
            payload=payload,
            site_name=settings.worker_site_name,
        )
        action.result = {"queued_task_id": task.id, "delegated": True}
        await db.commit()
        return True

    async def _dispatch_action(self, action: ActionHistory) -> tuple[bool, dict | None, str | None]:
        if action.action_template not in {
            ActionTemplate.restart_resource,
            ActionTemplate.start_resource,
            ActionTemplate.stop_resource,
        }:
            return False, None, f"Unsupported action template: {action.action_template}"

        return await self._execute_resource_action(
            action_template=action.action_template,
            target=action.target_resource,
            raw_parameters=action.parameters or {},
        )

    async def _execute_resource_action(
        self,
        action_template: ActionTemplate,
        target: str,
        raw_parameters: dict,
    ) -> tuple[bool, dict | None, str | None]:
        """Execute a resource action using plugin routing where available."""

        params = self._extract_effective_params(raw_parameters)

        if target.startswith("docker://"):
            return await self._execute_docker_via_plugin(action_template, target, params)

        if target.startswith("proxmox://"):
            return await self._execute_proxmox_legacy(action_template, target)

        return False, None, f"Action not supported for {target}"

    def _extract_effective_params(self, raw_parameters: dict) -> dict:
        """Extract effective parameters from either direct or wrapped todo shape."""

        nested_params = raw_parameters.get("params")
        if isinstance(nested_params, dict):
            return nested_params
        return raw_parameters

    async def _execute_docker_via_plugin(
        self,
        action_template: ActionTemplate,
        target: str,
        params: dict,
    ) -> tuple[bool, dict | None, str | None]:
        action_map = {
            ActionTemplate.restart_resource: "restart",
            ActionTemplate.start_resource: "start",
            ActionTemplate.stop_resource: "stop",
        }
        plugin_action_name = action_map.get(action_template)
        if not plugin_action_name:
            return False, None, f"No docker plugin action mapping for {action_template}"

        plugin = execution_registry.get("docker")
        plugin_action = PluginAction(
            action=plugin_action_name,
            target=target,
            params=params,
            metadata={"source": "plan_executor"},
        )

        pre_ok, pre_msg = await plugin.validate_pre(plugin_action)
        if not pre_ok:
            return False, None, f"Plugin pre-validation failed: {pre_msg}"

        result = await plugin.execute(plugin_action)

        post_ok, post_msg = await plugin.validate_post(plugin_action, result)
        if not post_ok:
            return False, result, f"Plugin post-validation failed: {post_msg}"

        if not result.get("success"):
            return False, result, result.get("error") or "Docker plugin execution failed"

        return True, result, None

    async def _execute_proxmox_legacy(
        self,
        action_template: ActionTemplate,
        target: str,
    ) -> tuple[bool, dict | None, str | None]:
        """Legacy path retained until Proxmox execution plugin is introduced."""

        if action_template != ActionTemplate.restart_resource:
            return False, None, f"{action_template} not supported for {target}"

        parts = target.split("://")[-1].split("/")
        if len(parts) < 3:
            return False, None, f"Invalid Proxmox target format: {target}"

        node = parts[0]
        type_str = parts[1]
        vmid = int(parts[2])

        try:
            ok = await proxmox_adapter.reboot_resource(node, type_str, vmid)
            if ok:
                return True, {"message": f"Reboot sent to {type_str} {vmid} on {node}"}, None
            return False, None, f"Reboot failed for {type_str} {vmid} on {node}"
        except Exception as e:
            return False, None, str(e)


plan_executor = PlanExecutor()
