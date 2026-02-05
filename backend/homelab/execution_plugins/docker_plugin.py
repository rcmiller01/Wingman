"""Built-in Docker execution plugin."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from homelab.adapters.docker_adapter import docker_adapter

from .base import ExecutionPlugin
from .models import PluginAction, PluginExecutionResult

_DOCKER_TARGET_PATTERN = re.compile(r"^docker://([a-zA-Z0-9][a-zA-Z0-9_.-]{0,127})$")


class DockerPlugin(ExecutionPlugin):
    """Execution plugin for Docker container lifecycle actions."""

    @property
    def plugin_id(self) -> str:
        return "docker"

    @property
    def supported_actions(self) -> list[str]:
        return ["restart", "start", "stop"]

    async def validate_pre(self, action: PluginAction) -> tuple[bool, str]:
        if action.action not in self.supported_actions:
            return False, f"Unsupported docker action: {action.action}"

        match = _DOCKER_TARGET_PATTERN.match(action.target)
        if not match:
            return False, f"Invalid Docker target format: {action.target}"

        timeout = action.params.get("timeout")
        if timeout is not None:
            try:
                timeout_value = int(timeout)
            except (TypeError, ValueError):
                return False, "Timeout must be an integer"
            if timeout_value < 1 or timeout_value > 300:
                return False, "Timeout must be between 1 and 300 seconds"

        return True, "ok"

    async def execute(self, action: PluginAction) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        container_id = _DOCKER_TARGET_PATTERN.match(action.target).group(1)  # validated by caller

        success = False
        error: str | None = None
        error_code: str | None = None

        try:
            if action.action == "restart":
                timeout = int(action.params.get("timeout", 10))
                success = await docker_adapter.restart_container(container_id, timeout=timeout)
            elif action.action == "start":
                success = await docker_adapter.start_container(container_id)
            elif action.action == "stop":
                timeout = int(action.params.get("timeout", 10))
                success = await docker_adapter.stop_container(container_id, timeout=timeout)
            else:
                error = f"Unsupported docker action: {action.action}"
                error_code = "VALIDATION_ERROR"
        except Exception as exc:  # defensive catch around adapter runtime issues
            success = False
            error = str(exc)
            error_code = "EXECUTION_ERROR"

        if not success and error is None:
            error = f"Docker action failed: {action.action} on {container_id}"
            error_code = "EXECUTION_ERROR"

        result = PluginExecutionResult(
            success=success,
            plugin_id=self.plugin_id,
            action=action.action,
            target=action.target,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            data={"container": container_id},
            error=error,
            error_code=error_code,
        )
        return result.to_dict()

    async def validate_post(self, action: PluginAction, result: dict[str, Any]) -> tuple[bool, str]:
        if not result.get("success"):
            return False, result.get("error") or "Execution failed"
        return True, "ok"

    async def rollback(self, action: PluginAction, result: dict[str, Any]) -> bool:
        # Phase 1 MVP: no automatic rollback for container lifecycle operations.
        return False
