"""Inventory API endpoints for containers and VMs."""

from fastapi import APIRouter
from homelab.adapters import docker_adapter, proxmox_adapter
from homelab.config import get_settings
from homelab.scheduler import scheduler

router = APIRouter(prefix="/api/inventory", tags=["inventory"])
settings = get_settings()


@router.get("/status")
async def get_inventory_status():
    """Get adapter connection status (legacy for frontend compatibility)."""
    return await get_full_inventory()


@router.get("/containers")
async def list_containers():
    """List all Docker containers."""
    containers = await docker_adapter.list_containers(all=True)
    return {
        "count": len(containers),
        "containers": containers,
    }


@router.get("/containers/{container_id}")
async def get_container(container_id: str):
    """Get a specific container."""
    container = await docker_adapter.get_container(container_id)
    if not container:
        return {"error": "Container not found"}
    return container


@router.get("/nodes")
async def list_nodes():
    """List all Proxmox nodes."""
    nodes = await proxmox_adapter.list_nodes()
    return {
        "count": len(nodes),
        "nodes": nodes,
    }


@router.get("/vms")
async def list_vms():
    """List all VMs across all nodes."""
    vms = await proxmox_adapter.list_vms()
    return {
        "count": len(vms),
        "vms": vms,
    }


@router.get("/lxcs")
async def list_lxcs():
    """List all LXC containers across all nodes."""
    lxcs = await proxmox_adapter.list_lxcs()
    return {
        "count": len(lxcs),
        "lxcs": lxcs,
    }


@router.get("/all")
async def get_full_inventory():
    """Get complete infrastructure inventory in frontend format."""
    if not proxmox_adapter.is_connected:
        await proxmox_adapter._check_connection()
        
    containers = await docker_adapter.list_containers(all=True)
    nodes = await proxmox_adapter.list_nodes()
    vms = await proxmox_adapter.list_vms()
    lxcs = await proxmox_adapter.list_lxcs()
    
    return {
        "docker": {
            "available": docker_adapter.is_connected,
            "containers": containers,
        },
        "proxmox": {
            "available": proxmox_adapter.is_connected,
            "configured": bool(settings.proxmox_host and settings.proxmox_user),
            "nodes": [{"node": n["name"], "status": n["status"]} for n in nodes],
            "vms": vms + lxcs,
        },
        "collector": {
            "running": scheduler.running,
            "intervalSeconds": 60,
        }
    }
