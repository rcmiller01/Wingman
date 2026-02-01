"""Docker adapter for container management."""

import docker
from docker.errors import DockerException, NotFound
from typing import Any
from datetime import datetime, timedelta


class DockerAdapter:
    """Adapter for Docker API operations."""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            self._connected = True
        except DockerException as e:
            print(f"[DockerAdapter] Failed to connect: {e}")
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
            print(f"[DockerAdapter] Error listing containers: {e}")
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
            print(f"[DockerAdapter] Error getting container {container_id}: {e}")
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
            print(f"[DockerAdapter] Error fetching logs for {container_id}: {e}")
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
            print(f"[DockerAdapter] Error restarting {container_id}: {e}")
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
            print(f"[DockerAdapter] Error starting {container_id}: {e}")
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
            print(f"[DockerAdapter] Error stopping {container_id}: {e}")
            return False
    
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
                # Parse ISO timestamp
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
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
