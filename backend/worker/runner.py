"""Task dispatch router for worker runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homelab.collectors.fact_collector import fact_collector
from homelab.execution_plugins import PluginAction, execution_registry
from homelab.execution_plugins.errors import PluginValidationError
from homelab.storage.database import async_session_maker
from homelab.workers.schemas import WorkerTaskEnvelope


class TaskRunner:
    """Routes tasks to execution handlers."""

    async def run(self, task: WorkerTaskEnvelope) -> tuple[str, dict[str, Any]]:
        if task.task_type == "collect_facts":
            return await self._collect_facts(task)
        if task.task_type == "execute_script":
            return await self._execute_script(task)
        if task.task_type == "execute_action":
            return await self._execute_action(task)

        return "execution_result", {
            "success": False,
            "error_code": "UNSUPPORTED_TASK",
            "error": f"Unsupported task type: {task.task_type}",
            "task_type": task.task_type,
        }

    async def _collect_facts(self, task: WorkerTaskEnvelope) -> tuple[str, dict[str, Any]]:
        async with async_session_maker() as session:
            counts = await fact_collector.collect_all(session)
            await session.commit()

        return "facts", {
            "success": True,
            "task_id": task.task_id,
            "collected_counts": counts,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "worker_id": task.worker_id,
        }

    async def _execute_script(self, task: WorkerTaskEnvelope) -> tuple[str, dict[str, Any]]:
        payload = task.payload or {}
        script_plugin = execution_registry.get("script")
        action = payload.get("action", "run_bash")
        target = payload.get("target", "local://worker")
        params = payload.get("params", {})

        plugin_action = PluginAction(
            action=action,
            target=target,
            params=params,
            metadata={"task_id": task.task_id, "worker_id": task.worker_id, "source": "worker"},
        )

        try:
            pre_ok, pre_msg = await script_plugin.validate_pre(plugin_action)
            if not pre_ok:
                return "execution_result", {
                    "success": False,
                    "error_code": "VALIDATION_ERROR",
                    "error": pre_msg,
                }
            result = await script_plugin.execute(plugin_action)
            post_ok, post_msg = await script_plugin.validate_post(plugin_action, result)
            if not post_ok:
                return "execution_result", {
                    "success": False,
                    "error_code": "POSTCHECK_ERROR",
                    "error": post_msg,
                    "result": result,
                }
            if result.get("success"):
                return "execution_result", {
                    "success": True,
                    "error_code": None,
                    "result": result,
                    "policy": {"allow_cloud_llm": False, "mode": "worker"},
                }
            return "execution_result", {
                "success": False,
                "error_code": result.get("error_code") or "EXECUTION_ERROR",
                "error": result.get("error") or "script execution failed",
                "result": result,
            }
        except PluginValidationError as exc:
            return "execution_result", {
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "error": str(exc),
            }
        except TimeoutError as exc:
            return "execution_result", {
                "success": False,
                "error_code": "TIMEOUT_ERROR",
                "error": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return "execution_result", {
                "success": False,
                "error_code": "EXECUTION_ERROR",
                "error": str(exc),
            }
