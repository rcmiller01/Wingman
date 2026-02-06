"""Built-in Script execution plugin (sandboxed subprocess MVP)."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from .base import ExecutionPlugin
from .models import PluginAction, PluginExecutionResult

SUPPORTED_ACTIONS = ["run_bash", "run_python"]
MAX_TIMEOUT_SECONDS = 300
MAX_SCRIPT_LENGTH = 4000
MAX_OUTPUT_CHARS = 4000

# MVP hard-block list for obviously dangerous operations.
_BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\brm\s+-rf\b",
        r"\bmkfs\b",
        r"\bdd\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r"\binit\s+0\b",
    ]
]


class ScriptPlugin(ExecutionPlugin):
    """Execution plugin for controlled bash/python script execution."""

    @property
    def plugin_id(self) -> str:
        return "script"

    @property
    def supported_actions(self) -> list[str]:
        return SUPPORTED_ACTIONS

    async def validate_pre(self, action: PluginAction) -> tuple[bool, str]:
        if action.action not in self.supported_actions:
            return False, f"Unsupported script action: {action.action}"

        script = self._get_script_content(action)
        if not script.strip():
            return False, "Script content cannot be empty"
        if len(script) > MAX_SCRIPT_LENGTH:
            return False, f"Script content exceeds {MAX_SCRIPT_LENGTH} characters"

        timeout = action.params.get("timeout", 30)
        try:
            timeout_value = int(timeout)
        except (TypeError, ValueError):
            return False, "Timeout must be an integer"

        if timeout_value < 1 or timeout_value > MAX_TIMEOUT_SECONDS:
            return False, f"Timeout must be between 1 and {MAX_TIMEOUT_SECONDS} seconds"

        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(script):
                return False, "Script contains blocked operation"

        return True, "ok"

    async def execute(self, action: PluginAction) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        script = self._get_script_content(action)
        timeout = int(action.params.get("timeout", 30))

        if action.action == "run_bash":
            cmd = ["bash", "-c", script]
        elif action.action == "run_python":
            cmd = ["python", "-c", script]
        else:
            return PluginExecutionResult(
                success=False,
                plugin_id=self.plugin_id,
                action=action.action,
                target=action.target,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                data={},
                error=f"Unsupported script action: {action.action}",
                error_code="VALIDATION_ERROR",
            ).to_dict()

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
            truncated = False
            if len(stdout) > MAX_OUTPUT_CHARS:
                stdout = stdout[:MAX_OUTPUT_CHARS]
                truncated = True
            if len(stderr) > MAX_OUTPUT_CHARS:
                stderr = stderr[:MAX_OUTPUT_CHARS]
                truncated = True

            success = proc.returncode == 0
            error = None if success else (stderr.strip() or f"Script exited with code {proc.returncode}")
            error_code = None if success else "EXECUTION_ERROR"
            data = {
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "truncated": truncated,
            }
        except asyncio.TimeoutError:
            # Kill the orphaned subprocess to prevent zombies
            if proc is not None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            success = False
            error = f"Script timed out after {timeout} seconds"
            error_code = "EXECUTION_ERROR"
            data = {"exit_code": None, "stdout": "", "stderr": "", "truncated": False}
        except Exception as exc:
            # Clean up subprocess on unexpected errors
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
            success = False
            error = str(exc)
            error_code = "EXECUTION_ERROR"
            data = {"exit_code": None, "stdout": "", "stderr": "", "truncated": False}

        return PluginExecutionResult(
            success=success,
            plugin_id=self.plugin_id,
            action=action.action,
            target=action.target,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            data=data,
            error=error,
            error_code=error_code,
        ).to_dict()

    async def validate_post(self, action: PluginAction, result: dict[str, Any]) -> tuple[bool, str]:
        if result.get("success"):
            return True, "ok"
        return False, result.get("error") or "Execution failed"

    async def rollback(self, action: PluginAction, result: dict[str, Any]) -> bool:
        # Phase 1 MVP: script actions are not auto-rollbackable.
        return False

    def _get_script_content(self, action: PluginAction) -> str:
        key = "command" if action.action == "run_bash" else "code"
        return str(action.params.get(key, ""))
