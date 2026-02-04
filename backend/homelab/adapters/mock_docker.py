"""Mock Docker adapter for testing.

Provides deterministic, CI-safe responses without requiring Docker.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MockDockerAdapter:
    """Mock Docker adapter that returns canned responses."""
    
    def __init__(self):
        self._containers: dict[str, dict] = {}
        self._setup_default_containers()
        logger.debug("[MockDocker] Initialized mock Docker adapter")
    
    def _setup_default_containers(self) -> None:
        """Set up default mock containers."""
        self._containers = {
            "nginx-test": {
                "Id": "abc123def456",
                "Name": "/nginx-test",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "Paused": False,
                    "Restarting": False,
                    "StartedAt": "2024-01-01T00:00:00Z",
                },
                "Config": {
                    "Image": "nginx:latest",
                    "Labels": {"wingman.test": "true"},
                },
                "NetworkSettings": {
                    "Ports": {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]},
                },
            },
            "postgres-test": {
                "Id": "def789ghi012",
                "Name": "/postgres-test",
                "State": {
                    "Status": "running",
                    "Running": True,
                    "Paused": False,
                    "Restarting": False,
                    "StartedAt": "2024-01-01T00:00:00Z",
                },
                "Config": {
                    "Image": "postgres:15",
                    "Labels": {"wingman.test": "true"},
                },
                "NetworkSettings": {
                    "Ports": {"5432/tcp": [{"HostIp": "0.0.0.0", "HostPort": "5444"}]},
                },
            },
            "redis-test": {
                "Id": "ghi345jkl678",
                "Name": "/redis-test",
                "State": {
                    "Status": "exited",
                    "Running": False,
                    "Paused": False,
                    "Restarting": False,
                    "ExitCode": 0,
                    "FinishedAt": "2024-01-01T12:00:00Z",
                },
                "Config": {
                    "Image": "redis:7",
                    "Labels": {"wingman.test": "true"},
                },
                "NetworkSettings": {"Ports": {}},
            },
        }
    
    async def get_container(self, container_id: str) -> dict[str, Any]:
        """Get container details by ID or name."""
        # Normalize name
        name = container_id.lstrip("/")
        
        if name in self._containers:
            return self._containers[name]
        
        # Search by ID prefix
        for c_name, c_data in self._containers.items():
            if c_data["Id"].startswith(container_id):
                return c_data
        
        raise ValueError(f"Container not found: {container_id}")
    
    async def list_containers(self, all: bool = False) -> list[dict[str, Any]]:
        """List containers."""
        containers = []
        for name, data in self._containers.items():
            if all or data["State"]["Running"]:
                containers.append({
                    "Id": data["Id"],
                    "Names": [data["Name"]],
                    "Image": data["Config"]["Image"],
                    "State": data["State"]["Status"],
                    "Status": f"Up 1 hour" if data["State"]["Running"] else "Exited",
                    "Labels": data["Config"].get("Labels", {}),
                })
        return containers
    
    async def get_container_logs(
        self, 
        container_id: str, 
        tail: int = 100,
        since: Optional[str] = None,
    ) -> str:
        """Get container logs."""
        await self.get_container(container_id)  # Validate exists
        
        timestamp = datetime.now(timezone.utc).isoformat()
        return f"""[{timestamp}] Mock log line 1 for {container_id}
[{timestamp}] Mock log line 2 for {container_id}
[{timestamp}] Container healthy
[{timestamp}] Processing request...
[{timestamp}] Request completed successfully"""
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> dict[str, Any]:
        """Restart a container."""
        container = await self.get_container(container_id)
        name = container["Name"].lstrip("/")
        
        # Update state
        self._containers[name]["State"]["Status"] = "running"
        self._containers[name]["State"]["Running"] = True
        self._containers[name]["State"]["StartedAt"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"[MockDocker] Restarted container: {container_id}")
        return {
            "success": True,
            "container": container_id,
            "action": "restart",
            "duration_ms": 1500,
        }
    
    async def start_container(self, container_id: str) -> dict[str, Any]:
        """Start a stopped container."""
        container = await self.get_container(container_id)
        name = container["Name"].lstrip("/")
        
        if self._containers[name]["State"]["Running"]:
            return {
                "success": True,
                "container": container_id,
                "action": "start",
                "message": "Container already running",
            }
        
        self._containers[name]["State"]["Status"] = "running"
        self._containers[name]["State"]["Running"] = True
        self._containers[name]["State"]["StartedAt"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"[MockDocker] Started container: {container_id}")
        return {
            "success": True,
            "container": container_id,
            "action": "start",
        }
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> dict[str, Any]:
        """Stop a running container."""
        container = await self.get_container(container_id)
        name = container["Name"].lstrip("/")
        
        self._containers[name]["State"]["Status"] = "exited"
        self._containers[name]["State"]["Running"] = False
        self._containers[name]["State"]["ExitCode"] = 0
        self._containers[name]["State"]["FinishedAt"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"[MockDocker] Stopped container: {container_id}")
        return {
            "success": True,
            "container": container_id,
            "action": "stop",
        }
    
    async def inspect_container(self, container_id: str) -> dict[str, Any]:
        """Get detailed container information."""
        return await self.get_container(container_id)
    
    async def get_container_stats(self, container_id: str) -> dict[str, Any]:
        """Get container resource stats."""
        await self.get_container(container_id)  # Validate exists
        
        return {
            "name": container_id,
            "cpu_percent": "0.15%",
            "mem_usage": "128MiB / 512MiB",
            "mem_percent": "25.0%",
            "net_io": "1.2MB / 500KB",
            "block_io": "50MB / 10MB",
            "pids": 10,
        }
    
    async def execute_command(self, container_id: str, command: list[str]) -> dict[str, Any]:
        """Execute a command in a container."""
        await self.get_container(container_id)  # Validate exists
        
        return {
            "exit_code": 0,
            "output": f"Mock output for command: {' '.join(command)}",
            "container": container_id,
        }
    
    # Additional methods for mock-specific functionality
    def add_container(self, name: str, data: dict) -> None:
        """Add a mock container (for test setup)."""
        self._containers[name] = data
    
    def remove_container(self, name: str) -> None:
        """Remove a mock container (for test setup)."""
        self._containers.pop(name, None)
    
    def reset(self) -> None:
        """Reset to default state."""
        self._setup_default_containers()
