"""Adapters package."""
from homelab.adapters.docker_adapter import docker_adapter, DockerAdapter
from homelab.adapters.proxmox_adapter import proxmox_adapter, ProxmoxAdapter

__all__ = [
    "docker_adapter",
    "DockerAdapter",
    "proxmox_adapter", 
    "ProxmoxAdapter",
]
