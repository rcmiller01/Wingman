"""Execution modes for skill runner - mock, integration, lab.

Provides three execution modes:
- MOCK: No real execution, returns canned responses (unit tests, demos)
- INTEGRATION: Uses real adapters but against test fixtures (integration tests)
- LAB: Real execution against actual infrastructure (production)

The mode is determined by:
1. Environment variable WINGMAN_EXECUTION_MODE
2. Per-execution override in the API
3. Default based on detected environment
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution mode for skill runner."""
    mock = "mock"             # No real execution, canned responses
    integration = "integration"  # Real adapters, test fixtures
    lab = "lab"               # Real execution, production infrastructure


@dataclass
class MockResponse:
    """A canned response for mock mode."""
    success: bool
    output: dict[str, Any]
    delay_seconds: float = 0.1  # Simulated latency
    error_message: str | None = None


# Default mock responses by skill ID pattern
DEFAULT_MOCK_RESPONSES: dict[str, MockResponse] = {
    # Diagnostics - always succeed
    "diag-container-logs": MockResponse(
        success=True,
        output={
            "logs": [
                {"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "message": "Container started"},
                {"timestamp": "2024-01-01T12:00:01Z", "level": "INFO", "message": "Listening on port 8080"},
            ],
            "line_count": 2,
        }
    ),
    "diag-container-inspect": MockResponse(
        success=True,
        output={
            "Id": "mock-container-123",
            "State": {"Status": "running", "Running": True},
            "Config": {"Image": "nginx:latest"},
        }
    ),
    "diag-vm-status": MockResponse(
        success=True,
        output={
            "vmid": "100",
            "status": "running",
            "cpu": 0.05,
            "mem": 512 * 1024 * 1024,
            "maxmem": 2048 * 1024 * 1024,
        }
    ),
    # Remediation - succeed by default
    "rem-restart-container": MockResponse(
        success=True,
        output={"restarted": True, "container": "mock-container", "duration_ms": 1500}
    ),
    "rem-restart-vm": MockResponse(
        success=True,
        output={"rebooted": True, "vmid": "100", "node": "pve"}
    ),
    "rem-restart-lxc": MockResponse(
        success=True,
        output={"rebooted": True, "vmid": "200", "node": "pve"}
    ),
    "rem-stop-container": MockResponse(
        success=True,
        output={"stopped": True, "container": "mock-container"}
    ),
    "rem-stop-vm": MockResponse(
        success=True,
        output={"stopped": True, "vmid": "100", "node": "pve"}
    ),
    # Maintenance
    "maint-prune-images": MockResponse(
        success=True,
        output={"pruned_count": 3, "space_reclaimed_mb": 512}
    ),
    "maint-create-snapshot": MockResponse(
        success=True,
        output={"snapshot_id": "snap-20240101", "vmid": "100"}
    ),
    # Additional diagnostics
    "diag-container-stats": MockResponse(
        success=True,
        output={
            "name": "mock-container",
            "cpu_percent": "0.15%",
            "mem_usage": "128MiB / 512MiB",
            "net_io": "1.2MB / 500KB",
            "block_io": "50MB / 10MB",
        }
    ),
    "diag-container-top": MockResponse(
        success=True,
        output={
            "processes": [
                {"pid": "1", "user": "root", "command": "nginx -g daemon off;"},
                {"pid": "12", "user": "nginx", "command": "nginx: worker process"},
            ]
        }
    ),
    "diag-container-health": MockResponse(
        success=True,
        output={
            "Status": "healthy",
            "FailingStreak": 0,
            "Log": [{"Start": "2024-01-01T00:00:00Z", "End": "2024-01-01T00:00:01Z", "ExitCode": 0}]
        }
    ),
    "diag-container-diff": MockResponse(
        success=True,
        output={
            "changes": [
                {"type": "C", "path": "/var/log"},
                {"type": "A", "path": "/var/log/app.log"},
            ]
        }
    ),
    "diag-container-port": MockResponse(
        success=True,
        output={"80/tcp": "0.0.0.0:8080", "443/tcp": "0.0.0.0:8443"}
    ),
    "diag-network-inspect": MockResponse(
        success=True,
        output={
            "Name": "bridge",
            "Driver": "bridge",
            "Containers": {"mock-container-123": {"Name": "mock-container", "IPv4Address": "172.17.0.2/16"}},
        }
    ),
    "diag-system-df": MockResponse(
        success=True,
        output={
            "images": {"total": 10, "size_mb": 2048, "reclaimable_mb": 512},
            "containers": {"total": 5, "running": 3, "size_mb": 256},
            "volumes": {"total": 8, "size_mb": 1024},
        }
    ),
    "diag-vm-config": MockResponse(
        success=True,
        output={
            "vmid": "100",
            "name": "mock-vm",
            "memory": 2048,
            "cores": 2,
            "sockets": 1,
            "net0": "virtio,bridge=vmbr0",
        }
    ),
    "diag-lxc-status": MockResponse(
        success=True,
        output={
            "vmid": "200",
            "status": "running",
            "cpu": 0.02,
            "mem": 256 * 1024 * 1024,
            "maxmem": 1024 * 1024 * 1024,
        }
    ),
    "diag-node-status": MockResponse(
        success=True,
        output={
            "node": "pve",
            "status": "online",
            "cpu": 0.15,
            "mem_used": 8 * 1024 * 1024 * 1024,
            "mem_total": 32 * 1024 * 1024 * 1024,
            "uptime": 86400 * 30,
        }
    ),
    # Additional remediation
    "rem-start-container": MockResponse(
        success=True,
        output={"started": True, "container": "mock-container"}
    ),
    "rem-pause-container": MockResponse(
        success=True,
        output={"paused": True, "container": "mock-container"}
    ),
    "rem-unpause-container": MockResponse(
        success=True,
        output={"unpaused": True, "container": "mock-container"}
    ),
    "rem-start-vm": MockResponse(
        success=True,
        output={"started": True, "vmid": "100", "node": "pve"}
    ),
    "rem-start-lxc": MockResponse(
        success=True,
        output={"started": True, "vmid": "200", "node": "pve"}
    ),
    "rem-stop-lxc": MockResponse(
        success=True,
        output={"stopped": True, "vmid": "200", "node": "pve"}
    ),
    # Additional maintenance
    "maint-prune-containers": MockResponse(
        success=True,
        output={"pruned_count": 5, "space_reclaimed_mb": 128}
    ),
    "maint-prune-volumes": MockResponse(
        success=True,
        output={"pruned_count": 3, "space_reclaimed_mb": 2048}
    ),
    "maint-prune-networks": MockResponse(
        success=True,
        output={"pruned_count": 2, "networks": ["unused-net-1", "unused-net-2"]}
    ),
    "maint-system-prune": MockResponse(
        success=True,
        output={"pruned_images": 5, "pruned_containers": 3, "pruned_volumes": 2, "space_reclaimed_mb": 4096}
    ),
    "maint-delete-snapshot": MockResponse(
        success=True,
        output={"deleted": True, "snapname": "snap-20240101", "vmid": "100"}
    ),
    "maint-rollback-snapshot": MockResponse(
        success=True,
        output={"rolled_back": True, "snapname": "snap-20240101", "vmid": "100"}
    ),
    "maint-create-lxc-snapshot": MockResponse(
        success=True,
        output={"snapshot_id": "snap-lxc-20240101", "vmid": "200"}
    ),
    # Monitoring
    "mon-container-events": MockResponse(
        success=True,
        output={
            "events": [
                {"time": "2024-01-01T00:00:00Z", "type": "container", "action": "start"},
                {"time": "2024-01-01T00:01:00Z", "type": "container", "action": "health_status: healthy"},
            ]
        }
    ),
    "mon-system-events": MockResponse(
        success=True,
        output={
            "events": [
                {"time": "2024-01-01T00:00:00Z", "type": "image", "action": "pull"},
                {"time": "2024-01-01T00:00:30Z", "type": "container", "action": "create"},
                {"time": "2024-01-01T00:00:35Z", "type": "container", "action": "start"},
            ]
        }
    ),
}

# Responses that simulate failures (for testing error paths)
FAILURE_MOCK_RESPONSES: dict[str, MockResponse] = {
    "rem-restart-container": MockResponse(
        success=False,
        output={},
        error_message="Container not found: mock-container"
    ),
    "rem-restart-vm": MockResponse(
        success=False,
        output={},
        error_message="VM 100 is locked (backup in progress)"
    ),
}


class ExecutionModeManager:
    """Manages execution mode and provides mode-appropriate handlers."""
    
    def __init__(self):
        self._mode: ExecutionMode = self._detect_mode()
        self._custom_mock_responses: dict[str, MockResponse] = {}
        self._force_failures: set[str] = set()  # Skill IDs that should fail in mock
        self._execution_hooks: list[Callable[[str, str, dict], Awaitable[None]]] = []
    
    def _detect_mode(self) -> ExecutionMode:
        """Detect execution mode from environment."""
        env_mode = os.environ.get("WINGMAN_EXECUTION_MODE", "").lower()
        
        if env_mode == "mock":
            return ExecutionMode.mock
        elif env_mode == "integration":
            return ExecutionMode.integration
        elif env_mode == "lab":
            return ExecutionMode.lab
        
        # Auto-detect based on environment
        if os.environ.get("PYTEST_CURRENT_TEST"):
            # Running in pytest
            return ExecutionMode.mock
        elif os.environ.get("CI"):
            # Running in CI
            return ExecutionMode.integration
        else:
            # Default to lab for production
            return ExecutionMode.lab
    
    @property
    def mode(self) -> ExecutionMode:
        """Get current execution mode."""
        return self._mode
    
    def set_mode(self, mode: ExecutionMode) -> None:
        """Set execution mode (useful for tests)."""
        old_mode = self._mode
        self._mode = mode
        logger.info(f"[ExecutionModeManager] Mode changed: {old_mode.value} → {mode.value}")
    
    def is_mock(self) -> bool:
        """Check if in mock mode."""
        return self._mode == ExecutionMode.mock
    
    def is_integration(self) -> bool:
        """Check if in integration mode."""
        return self._mode == ExecutionMode.integration
    
    def is_lab(self) -> bool:
        """Check if in lab/production mode."""
        return self._mode == ExecutionMode.lab
    
    def should_execute_real(self) -> bool:
        """Check if real execution should happen (integration or lab)."""
        return self._mode in (ExecutionMode.integration, ExecutionMode.lab)
    
    # Mock response management
    
    def register_mock_response(self, skill_id: str, response: MockResponse) -> None:
        """Register a custom mock response for a skill."""
        self._custom_mock_responses[skill_id] = response
        logger.debug(f"[ExecutionModeManager] Registered mock response for {skill_id}")
    
    def clear_mock_responses(self) -> None:
        """Clear all custom mock responses."""
        self._custom_mock_responses.clear()
        self._force_failures.clear()
    
    def force_failure(self, skill_id: str) -> None:
        """Force a skill to fail in mock mode (for testing error paths)."""
        self._force_failures.add(skill_id)
    
    def clear_forced_failures(self) -> None:
        """Clear forced failures."""
        self._force_failures.clear()
    
    def get_mock_response(self, skill_id: str) -> MockResponse:
        """Get mock response for a skill."""
        # Check forced failures first
        if skill_id in self._force_failures:
            return FAILURE_MOCK_RESPONSES.get(
                skill_id,
                MockResponse(success=False, output={}, error_message=f"Forced failure for {skill_id}")
            )
        
        # Check custom responses
        if skill_id in self._custom_mock_responses:
            return self._custom_mock_responses[skill_id]
        
        # Fall back to defaults
        if skill_id in DEFAULT_MOCK_RESPONSES:
            return DEFAULT_MOCK_RESPONSES[skill_id]
        
        # Generic success for unknown skills
        return MockResponse(
            success=True,
            output={"mock": True, "skill_id": skill_id, "timestamp": datetime.utcnow().isoformat()}
        )
    
    # Hooks for test observability
    
    def add_execution_hook(
        self, 
        hook: Callable[[str, str, dict], Awaitable[None]]
    ) -> None:
        """
        Add a hook that's called on every execution attempt.
        
        Hook signature: async def hook(skill_id: str, target: str, params: dict) -> None
        
        Useful for tests to observe execution patterns.
        """
        self._execution_hooks.append(hook)
    
    def clear_hooks(self) -> None:
        """Clear all execution hooks."""
        self._execution_hooks.clear()
    
    async def notify_hooks(self, skill_id: str, target: str, params: dict) -> None:
        """Notify all registered hooks of an execution."""
        for hook in self._execution_hooks:
            try:
                await hook(skill_id, target, params)
            except Exception as e:
                logger.warning(f"[ExecutionModeManager] Hook failed: {e}")
    
    def get_status(self) -> dict[str, Any]:
        """Get status information about execution mode."""
        return {
            "mode": self._mode.value,
            "custom_mock_responses": len(self._custom_mock_responses),
            "forced_failures": list(self._force_failures),
            "hooks_registered": len(self._execution_hooks),
            "description": {
                ExecutionMode.mock: "Mock mode - no real execution, canned responses",
                ExecutionMode.integration: "Integration mode - real adapters, test fixtures",
                ExecutionMode.lab: "Lab mode - real execution against infrastructure",
            }[self._mode],
        }


# Singleton instance
execution_mode_manager = ExecutionModeManager()


# Context manager for temporarily changing mode
class execution_mode_context:
    """Context manager for temporarily changing execution mode."""
    
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.previous_mode: ExecutionMode | None = None
    
    def __enter__(self):
        self.previous_mode = execution_mode_manager.mode
        execution_mode_manager.set_mode(self.mode)
        return execution_mode_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_mode is not None:
            execution_mode_manager.set_mode(self.previous_mode)
        return False


# Async version
class async_execution_mode_context:
    """Async context manager for temporarily changing execution mode."""
    
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.previous_mode: ExecutionMode | None = None
    
    async def __aenter__(self):
        self.previous_mode = execution_mode_manager.mode
        execution_mode_manager.set_mode(self.mode)
        return execution_mode_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.previous_mode is not None:
            execution_mode_manager.set_mode(self.previous_mode)
        return False
