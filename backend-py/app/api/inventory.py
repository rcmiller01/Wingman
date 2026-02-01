"""Inventory API endpoints for containers and VMs."""

from fastapi import APIRouter
from app.adapters import docker_adapter, proxmox_adapter

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/status")
async def get_inventory_status():
    """Get adapter connection status."""
    return {
        "docker": {
            "connected": docker_adapter.is_connected,
        },
        "proxmox": {
            "connected": proxmox_adapter.is_connected,
        },
    }


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
    """Get complete infrastructure inventory."""
    containers = await docker_adapter.list_containers(all=True)
    nodes = await proxmox_adapter.list_nodes()
    vms = await proxmox_adapter.list_vms()
    lxcs = await proxmox_adapter.list_lxcs()
    
    return {
        "docker": {
            "connected": docker_adapter.is_connected,
            "count": len(containers),
            "containers": containers,
        },
        "proxmox": {
            "connected": proxmox_adapter.is_connected,
            "nodes": {
                "count": len(nodes),
                "items": nodes,
            },
            "vms": {
                "count": len(vms),
                "items": vms,
            },
            "lxcs": {
                "count": len(lxcs),
                "items": lxcs,
            },
        },
    }
