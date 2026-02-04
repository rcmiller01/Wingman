"""Dependency wiring layer.

Provides adapters and safety policies based on execution mode.
Only changes adapter implementations and safety constraints - never business logic.
"""

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional, Any

from homelab.runtime.mode import ExecutionMode, get_execution_mode
from homelab.runtime.safety import (
    SafetyPolicy,
    MockSafetyPolicy,
    IntegrationSafetyPolicy,
    LabSafetyPolicy,
    get_safety_policy_for_mode,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Adapter Protocols (contracts that all adapters must implement)
# ============================================================================

@runtime_checkable
class DockerAdapterProtocol(Protocol):
    """Protocol defining the Docker adapter interface."""
    
    async def get_container(self, container_id: str) -> dict[str, Any]:
        """Get container details by ID or name."""
        ...
    
    async def list_containers(self, all: bool = False) -> list[dict[str, Any]]:
        """List containers."""
        ...
    
    async def get_container_logs(
        self, 
        container_id: str, 
        tail: int = 100,
        since: Optional[str] = None,
    ) -> str:
        """Get container logs."""
        ...
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> dict[str, Any]:
        """Restart a container."""
        ...
    
    async def start_container(self, container_id: str) -> dict[str, Any]:
        """Start a stopped container."""
        ...
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> dict[str, Any]:
        """Stop a running container."""
        ...
    
    async def inspect_container(self, container_id: str) -> dict[str, Any]:
        """Get detailed container information."""
        ...
    
    async def get_container_stats(self, container_id: str) -> dict[str, Any]:
        """Get container resource stats."""
        ...
    
    async def execute_command(self, container_id: str, command: list[str]) -> dict[str, Any]:
        """Execute a command in a container."""
        ...


@runtime_checkable
class ProxmoxAdapterProtocol(Protocol):
    """Protocol defining the Proxmox adapter interface."""
    
    async def get_node_status(self, node: str) -> dict[str, Any]:
        """Get node status."""
        ...
    
    async def get_vm_status(self, node: str, vmid: int) -> dict[str, Any]:
        """Get VM status."""
        ...
    
    async def get_lxc_status(self, node: str, vmid: int) -> dict[str, Any]:
        """Get LXC container status."""
        ...
    
    async def start_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Start a VM."""
        ...
    
    async def stop_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop a VM."""
        ...
    
    async def restart_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Restart a VM."""
        ...
    
    async def start_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Start an LXC container."""
        ...
    
    async def stop_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop an LXC container."""
        ...
    
    async def restart_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Restart an LXC container."""
        ...
    
    async def create_snapshot(
        self, 
        node: str, 
        vmid: int, 
        snapname: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a VM snapshot."""
        ...
    
    async def list_snapshots(self, node: str, vmid: int) -> list[dict[str, Any]]:
        """List VM snapshots."""
        ...


# ============================================================================
# Runtime Dependencies Container
# ============================================================================

@dataclass
class RuntimeDependencies:
    """Container for runtime dependencies based on execution mode."""
    
    mode: ExecutionMode
    docker_adapter: DockerAdapterProtocol
    proxmox_adapter: ProxmoxAdapterProtocol
    safety_policy: SafetyPolicy
    
    def __post_init__(self):
        logger.info(
            f"[Runtime] Dependencies initialized: mode={self.mode.value}, "
            f"docker={type(self.docker_adapter).__name__}, "
            f"proxmox={type(self.proxmox_adapter).__name__}, "
            f"safety={type(self.safety_policy).__name__}"
        )


# ============================================================================
# Adapter Factory Functions
# ============================================================================

def _get_mock_docker_adapter() -> DockerAdapterProtocol:
    """Get mock Docker adapter."""
    from homelab.adapters.mock_docker import MockDockerAdapter
    return MockDockerAdapter()


def _get_real_docker_adapter() -> DockerAdapterProtocol:
    """Get real Docker adapter."""
    from homelab.adapters.docker_adapter import DockerAdapter
    return DockerAdapter()


def _get_mock_proxmox_adapter() -> ProxmoxAdapterProtocol:
    """Get mock Proxmox adapter."""
    from homelab.adapters.mock_proxmox import MockProxmoxAdapter
    return MockProxmoxAdapter()


def _get_real_proxmox_adapter() -> ProxmoxAdapterProtocol:
    """Get real Proxmox adapter."""
    from homelab.adapters.proxmox_adapter import ProxmoxAdapter
    return ProxmoxAdapter()


def get_adapters(mode: Optional[ExecutionMode] = None) -> RuntimeDependencies:
    """Get adapters configured for the specified execution mode.
    
    Args:
        mode: Execution mode. If None, uses current mode from context/env.
        
    Returns:
        RuntimeDependencies with appropriately configured adapters.
    """
    if mode is None:
        mode = get_execution_mode()
    
    if mode == ExecutionMode.mock:
        return RuntimeDependencies(
            mode=mode,
            docker_adapter=_get_mock_docker_adapter(),
            proxmox_adapter=_get_mock_proxmox_adapter(),
            safety_policy=MockSafetyPolicy(),
        )
    
    elif mode == ExecutionMode.integration:
        return RuntimeDependencies(
            mode=mode,
            docker_adapter=_get_real_docker_adapter(),
            proxmox_adapter=_get_mock_proxmox_adapter(),  # Mock Proxmox in integration
            safety_policy=IntegrationSafetyPolicy(),
        )
    
    elif mode == ExecutionMode.lab:
        return RuntimeDependencies(
            mode=mode,
            docker_adapter=_get_real_docker_adapter(),
            proxmox_adapter=_get_real_proxmox_adapter(),
            safety_policy=LabSafetyPolicy(),
        )
    
    else:
        logger.warning(f"[Runtime] Unknown mode '{mode}', falling back to mock")
        return RuntimeDependencies(
            mode=ExecutionMode.mock,
            docker_adapter=_get_mock_docker_adapter(),
            proxmox_adapter=_get_mock_proxmox_adapter(),
            safety_policy=MockSafetyPolicy(),
        )


def get_safety_policy(mode: Optional[ExecutionMode] = None) -> SafetyPolicy:
    """Get safety policy for the specified execution mode.
    
    Args:
        mode: Execution mode. If None, uses current mode from context/env.
        
    Returns:
        SafetyPolicy configured for the mode.
    """
    if mode is None:
        mode = get_execution_mode()
    
    return get_safety_policy_for_mode(mode)


# ============================================================================
# Singleton-style cached dependencies (for app lifetime)
# ============================================================================

_cached_deps: Optional[RuntimeDependencies] = None


def get_cached_adapters() -> RuntimeDependencies:
    """Get cached adapters (created once per app lifetime).
    
    Use this in request handlers to avoid creating adapters repeatedly.
    """
    global _cached_deps
    
    current_mode = get_execution_mode()
    
    # Recreate if mode changed or not yet created
    if _cached_deps is None or _cached_deps.mode != current_mode:
        _cached_deps = get_adapters(current_mode)
    
    return _cached_deps


def reset_cached_adapters() -> None:
    """Reset cached adapters. Useful for tests."""
    global _cached_deps
    _cached_deps = None
