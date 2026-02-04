"""Adapters package."""
from homelab.adapters.docker_adapter import docker_adapter, DockerAdapter
from homelab.adapters.proxmox_adapter import proxmox_adapter, ProxmoxAdapter
from homelab.adapters.mock_docker import MockDockerAdapter
from homelab.adapters.mock_proxmox import MockProxmoxAdapter

__all__ = [
    # Real adapters
    "docker_adapter",
    "DockerAdapter",
    "proxmox_adapter", 
    "ProxmoxAdapter",
    # Mock adapters
    "MockDockerAdapter",
    "MockProxmoxAdapter",
]
