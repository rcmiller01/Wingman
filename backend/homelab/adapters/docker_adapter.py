"""Docker adapter for container management."""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from datetime import datetime, timedelta

import docker
from docker.errors import DockerException, NotFound

logger = logging.getLogger(__name__)

# Thread pool for running sync Docker client calls
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="docker")

# Safety constants
MAX_LOG_LINES = 1000
MAX_LOG_BYTES = 1024 * 1024  # 1MB
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300

# Input validation
_CONTAINER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

# Fields to strip from inspection (may contain secrets)
_SENSITIVE_INSPECTION_FIELDS = {'Env', 'Config.Env'}


class DockerAdapter:
    """Adapter for Docker API operations."""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            self._connected = True
        except DockerException as e:
            logger.error("[DockerAdapter] Failed to connect: %s", e)
            self.client = None
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def list_containers(self, all: bool = True) -> list[dict[str, Any]]:
        """List all containers with status information."""
        if not self.client:
            return []
        
        try:
            containers = self.client.containers.list(all=all)
            return [self._container_to_dict(c) for c in containers]
        except Exception as e:
            logger.error("[DockerAdapter] Error listing containers: %s", e)
            return []
    
    async def get_container(self, container_id: str) -> dict[str, Any] | None:
        """Get a single container by ID or name."""
        if not self.client:
            return None
        
        try:
            container = self.client.containers.get(container_id)
            return self._container_to_dict(container)
        except NotFound:
            return None
        except Exception as e:
            logger.error("[DockerAdapter] Error getting container %s: %s", container_id, e)
            return None
    
    async def get_logs(
        self, 
        container_id: str, 
        since_minutes: int = 60,
        tail: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch container logs."""
        if not self.client:
            return []
        
        try:
            container = self.client.containers.get(container_id)
            since = datetime.utcnow() - timedelta(minutes=since_minutes)
            
            # Fetch stdout and stderr separately for source tagging
            logs_stdout = container.logs(
                stdout=True, stderr=False, 
                since=since, tail=tail, timestamps=True
            ).decode("utf-8", errors="replace")
            
            logs_stderr = container.logs(
                stdout=False, stderr=True,
                since=since, tail=tail, timestamps=True
            ).decode("utf-8", errors="replace")
            
            entries = []
            for line in logs_stdout.splitlines():
                if line.strip():
                    entries.append(self._parse_log_line(line, "stdout"))
            for line in logs_stderr.splitlines():
                if line.strip():
                    entries.append(self._parse_log_line(line, "stderr"))
            
            # Sort by timestamp
            entries.sort(key=lambda x: x["timestamp"])
            return entries
            
        except NotFound:
            return []
        except Exception as e:
            logger.error("[DockerAdapter] Error fetching logs for %s: %s", container_id, e)
            return []
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """Restart a container. Returns success."""
        if not self.client:
            return False
        
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=timeout)
            return True
        except Exception as e:
            logger.error("[DockerAdapter] Error restarting %s: %s", container_id, e)
            return False
    
    async def start_container(self, container_id: str) -> bool:
        """Start a stopped container."""
        if not self.client:
            return False
        
        try:
            container = self.client.containers.get(container_id)
            container.start()
            return True
        except Exception as e:
            logger.error("[DockerAdapter] Error starting %s: %s", container_id, e)
            return False
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a running container."""
        if not self.client:
            return False
        
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            return True
        except Exception as e:
            logger.error("[DockerAdapter] Error stopping %s: %s", container_id, e)
            return False
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100,
        since: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> str:
        """
        Get container logs as a string with safety bounds.
        
        Args:
            container_id: Container ID or name
            tail: Max lines to return (capped at MAX_LOG_LINES)
            since: Optional timestamp to start from
            timeout: Max time to wait (capped at MAX_TIMEOUT_SECONDS)
        
        Returns:
            Log content as string, truncated if exceeds MAX_LOG_BYTES
        """
        if not self.client:
            return ""
        
        # Validate container ID
        if not container_id or not _CONTAINER_ID_PATTERN.match(container_id):
            logger.warning("[DockerAdapter] Invalid container ID: %s", container_id)
            return ""
        
        # Enforce bounds
        tail = min(max(1, tail), MAX_LOG_LINES)
        timeout = min(max(1, timeout), MAX_TIMEOUT_SECONDS)
        
        def _sync_get_logs():
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8", errors="replace")
        
        try:
            loop = asyncio.get_event_loop()
            logs = await asyncio.wait_for(
                loop.run_in_executor(_executor, _sync_get_logs),
                timeout=timeout
            )
            
            # Truncate if too large
            if len(logs) > MAX_LOG_BYTES:
                logs = logs[:MAX_LOG_BYTES] + "\n... [TRUNCATED - exceeded 1MB limit]"
            
            return logs
        except asyncio.TimeoutError:
            logger.warning("[DockerAdapter] Timeout getting logs for %s", container_id)
            return "[ERROR: Timeout retrieving logs]"
        except NotFound:
            logger.warning("[DockerAdapter] Container not found: %s", container_id)
            return ""
        except Exception as e:
            logger.error("[DockerAdapter] Error getting logs for %s: %s", container_id, e)
            return ""
    
    async def inspect_container(
        self,
        container_id: str,
        strip_secrets: bool = True,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any] | None:
        """
        Get detailed container inspection data with safety bounds.
        
        Args:
            container_id: Container ID or name
            strip_secrets: Remove environment variables and other sensitive data
            timeout: Max time to wait
        
        Returns:
            Container attributes dict, or None if not found/error
        """
        if not self.client:
            return None
        
        # Validate container ID
        if not container_id or not _CONTAINER_ID_PATTERN.match(container_id):
            logger.warning("[DockerAdapter] Invalid container ID: %s", container_id)
            return None
        
        timeout = min(max(1, timeout), MAX_TIMEOUT_SECONDS)
        
        def _sync_inspect():
            container = self.client.containers.get(container_id)
            return container.attrs
        
        try:
            loop = asyncio.get_event_loop()
            attrs = await asyncio.wait_for(
                loop.run_in_executor(_executor, _sync_inspect),
                timeout=timeout
            )
            
            if strip_secrets and attrs:
                attrs = self._strip_sensitive_fields(attrs)
            
            return attrs
        except asyncio.TimeoutError:
            logger.warning("[DockerAdapter] Timeout inspecting %s", container_id)
            return None
        except NotFound:
            return None
        except Exception as e:
            logger.error("[DockerAdapter] Error inspecting %s: %s", container_id, e)
            return None
    
    def _strip_sensitive_fields(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Remove potentially sensitive fields from container attributes."""
        import copy
        safe_attrs = copy.deepcopy(attrs)
        
        # Strip environment variables (may contain secrets)
        if "Config" in safe_attrs and "Env" in safe_attrs["Config"]:
            safe_attrs["Config"]["Env"] = ["[REDACTED - use docker inspect directly for env vars]"]
        
        # Strip any NetworkSettings credentials
        if "NetworkSettings" in safe_attrs:
            ns = safe_attrs["NetworkSettings"]
            if "Networks" in ns:
                for network in ns["Networks"].values():
                    if isinstance(network, dict):
                        network.pop("NetworkID", None)
                        network.pop("EndpointID", None)
        
        return safe_attrs
    
    async def prune_images(
        self,
        all: bool = False,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """
        Prune unused Docker images with timeout protection.
        
        Args:
            all: If True, remove all unused images (not just dangling)
            timeout: Max time to wait for prune operation
        """
        if not self.client:
            return {"error": "Docker client not connected"}
        
        timeout = min(max(1, timeout), MAX_TIMEOUT_SECONDS)
        
        def _sync_prune():
            return self.client.images.prune(filters={"dangling": not all})
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(_executor, _sync_prune),
                timeout=timeout
            )
            return {
                "images_deleted": len(result.get("ImagesDeleted", []) or []),
                "space_reclaimed": result.get("SpaceReclaimed", 0),
            }
        except asyncio.TimeoutError:
            logger.warning("[DockerAdapter] Timeout during image prune")
            return {"error": "Timeout during prune operation"}
        except Exception as e:
            logger.error("[DockerAdapter] Error pruning images: %s", e)
            return {"error": str(e)}
    
    async def inspect_container(self, container_id: str) -> dict[str, Any]:
        """Get detailed container information (full inspection)."""
        if not self.client:
            return {}
        
        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs.copy()
            
            # Strip sensitive fields
            if "Config" in attrs and "Env" in attrs["Config"]:
                attrs["Config"]["Env"] = "[REDACTED]"
            
            return attrs
        except NotFound:
            return {}
        except Exception as e:
            logger.error("[DockerAdapter] Error inspecting %s: %s", container_id, e)
            return {}
    
    async def get_container_stats(self, container_id: str) -> dict[str, Any]:
        """Get container resource stats (single snapshot, not stream)."""
        if not self.client:
            return {}
        
        def _sync_stats():
            container = self.client.containers.get(container_id)
            return container.stats(stream=False)
        
        try:
            loop = asyncio.get_event_loop()
            stats = await asyncio.wait_for(
                loop.run_in_executor(_executor, _sync_stats),
                timeout=DEFAULT_TIMEOUT_SECONDS
            )
            
            # Calculate CPU percentage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                        stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                           stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100 if system_delta > 0 else 0
            
            # Memory stats
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0
            
            return {
                "name": container_id,
                "cpu_percent": f"{cpu_percent:.2f}%",
                "mem_usage": f"{mem_usage / (1024*1024):.1f}MiB / {mem_limit / (1024*1024):.1f}MiB",
                "mem_percent": f"{mem_percent:.1f}%",
                "net_io": stats.get("networks", {}),
                "block_io": stats.get("blkio_stats", {}),
                "pids": stats.get("pids_stats", {}).get("current", 0),
            }
        except NotFound:
            return {}
        except Exception as e:
            logger.error("[DockerAdapter] Error getting stats for %s: %s", container_id, e)
            return {}
    
    async def execute_command(self, container_id: str, command: list[str]) -> dict[str, Any]:
        """Execute a command in a container."""
        if not self.client:
            return {"exit_code": -1, "output": "Docker client not connected"}
        
        def _sync_exec():
            container = self.client.containers.get(container_id)
            result = container.exec_run(command, demux=True)
            stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
            stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""
            return {
                "exit_code": result.exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "output": stdout + stderr,
            }
        
        try:
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(_executor, _sync_exec),
                timeout=DEFAULT_TIMEOUT_SECONDS
            )
        except NotFound:
            return {"exit_code": -1, "output": f"Container not found: {container_id}"}
        except Exception as e:
            logger.error("[DockerAdapter] Error executing command in %s: %s", container_id, e)
            return {"exit_code": -1, "output": str(e)}
    
    def _container_to_dict(self, container) -> dict[str, Any]:
        """Convert container object to dict."""
        attrs = container.attrs
        state = attrs.get("State", {})
        
        # Calculate restart count
        restart_count = state.get("RestartCount", 0)
        
        return {
            "id": container.id,
            "short_id": container.short_id,
            "name": container.name,
            "status": container.status,
            "state": container.status,
            "image": container.image.tags[0] if container.image.tags else str(container.image.id)[:12],
            "created": attrs.get("Created"),
            "started_at": state.get("StartedAt"),
            "finished_at": state.get("FinishedAt"),
            "restart_count": restart_count,
            "health": state.get("Health", {}).get("Status"),
            "ports": attrs.get("NetworkSettings", {}).get("Ports", {}),
            "resource_ref": f"docker://{container.id}",
        }
    
    def _parse_log_line(self, line: str, source: str) -> dict[str, Any]:
        """Parse a Docker log line with timestamp."""
        # Docker logs format: 2024-01-01T12:00:00.000000000Z content
        try:
            if " " in line:
                timestamp_str, content = line.split(" ", 1)
                # Parse ISO timestamp and convert to naive UTC
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Convert to naive datetime (UTC) for PostgreSQL
                timestamp = timestamp.replace(tzinfo=None)
            else:
                timestamp = datetime.utcnow()
                content = line
        except Exception:
            timestamp = datetime.utcnow()
            content = line
        
        return {
            "timestamp": timestamp,
            "content": content.strip(),
            "source": source,
        }


# Singleton instance
docker_adapter = DockerAdapter()
