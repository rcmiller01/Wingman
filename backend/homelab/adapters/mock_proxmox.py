"""Mock Proxmox adapter for testing.

Provides deterministic, CI-safe responses without requiring Proxmox.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MockProxmoxAdapter:
    """Mock Proxmox adapter that returns canned responses."""
    
    def __init__(self):
        self._nodes: dict[str, dict] = {}
        self._vms: dict[str, dict] = {}
        self._lxcs: dict[str, dict] = {}
        self._snapshots: dict[str, list] = {}
        self._setup_defaults()
        logger.debug("[MockProxmox] Initialized mock Proxmox adapter")
    
    def _setup_defaults(self) -> None:
        """Set up default mock resources."""
        # Default node
        self._nodes = {
            "pve": {
                "node": "pve",
                "status": "online",
                "cpu": 0.15,
                "maxcpu": 8,
                "mem": 8 * 1024 * 1024 * 1024,
                "maxmem": 32 * 1024 * 1024 * 1024,
                "disk": 100 * 1024 * 1024 * 1024,
                "maxdisk": 500 * 1024 * 1024 * 1024,
                "uptime": 86400 * 30,
            },
            "pve2": {
                "node": "pve2",
                "status": "online",
                "cpu": 0.25,
                "maxcpu": 4,
                "mem": 4 * 1024 * 1024 * 1024,
                "maxmem": 16 * 1024 * 1024 * 1024,
                "disk": 50 * 1024 * 1024 * 1024,
                "maxdisk": 250 * 1024 * 1024 * 1024,
                "uptime": 86400 * 15,
            },
        }
        
        # Default VMs
        self._vms = {
            "pve:100": {
                "vmid": 100,
                "name": "test-vm-1",
                "node": "pve",
                "status": "running",
                "cpu": 0.05,
                "maxcpu": 2,
                "mem": 512 * 1024 * 1024,
                "maxmem": 2048 * 1024 * 1024,
                "disk": 10 * 1024 * 1024 * 1024,
                "maxdisk": 50 * 1024 * 1024 * 1024,
                "uptime": 86400,
            },
            "pve:101": {
                "vmid": 101,
                "name": "test-vm-2",
                "node": "pve",
                "status": "stopped",
                "cpu": 0,
                "maxcpu": 4,
                "mem": 0,
                "maxmem": 4096 * 1024 * 1024,
                "disk": 20 * 1024 * 1024 * 1024,
                "maxdisk": 100 * 1024 * 1024 * 1024,
                "uptime": 0,
            },
        }
        
        # Default LXCs
        self._lxcs = {
            "pve:200": {
                "vmid": 200,
                "name": "test-lxc-1",
                "node": "pve",
                "status": "running",
                "cpu": 0.02,
                "maxcpu": 1,
                "mem": 256 * 1024 * 1024,
                "maxmem": 1024 * 1024 * 1024,
                "disk": 5 * 1024 * 1024 * 1024,
                "maxdisk": 20 * 1024 * 1024 * 1024,
                "uptime": 86400 * 7,
            },
        }
        
        # Default snapshots
        self._snapshots = {
            "pve:100": [
                {
                    "name": "before-update",
                    "description": "Snapshot before system update",
                    "snaptime": int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp()),
                    "vmstate": False,
                },
            ],
        }
    
    async def get_node_status(self, node: str) -> dict[str, Any]:
        """Get node status."""
        if node not in self._nodes:
            raise ValueError(f"Node not found: {node}")
        return self._nodes[node]
    
    async def get_vm_status(self, node: str, vmid: int) -> dict[str, Any]:
        """Get VM status."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        return self._vms[key]
    
    async def get_lxc_status(self, node: str, vmid: int) -> dict[str, Any]:
        """Get LXC container status."""
        key = f"{node}:{vmid}"
        if key not in self._lxcs:
            raise ValueError(f"LXC not found: {vmid} on {node}")
        return self._lxcs[key]
    
    async def start_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Start a VM."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        
        self._vms[key]["status"] = "running"
        self._vms[key]["uptime"] = 0
        
        logger.info(f"[MockProxmox] Started VM {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "start",
            "task": f"UPID:{node}:00000001:00000001:00000001:qmstart:{vmid}:root@pam:",
        }
    
    async def stop_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop a VM."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        
        self._vms[key]["status"] = "stopped"
        self._vms[key]["uptime"] = 0
        self._vms[key]["cpu"] = 0
        self._vms[key]["mem"] = 0
        
        logger.info(f"[MockProxmox] Stopped VM {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "stop",
            "task": f"UPID:{node}:00000001:00000001:00000001:qmstop:{vmid}:root@pam:",
        }
    
    async def restart_vm(self, node: str, vmid: int) -> dict[str, Any]:
        """Restart a VM."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        
        self._vms[key]["status"] = "running"
        self._vms[key]["uptime"] = 0
        
        logger.info(f"[MockProxmox] Restarted VM {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "restart",
            "task": f"UPID:{node}:00000001:00000001:00000001:qmreboot:{vmid}:root@pam:",
        }
    
    async def start_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Start an LXC container."""
        key = f"{node}:{vmid}"
        if key not in self._lxcs:
            raise ValueError(f"LXC not found: {vmid} on {node}")
        
        self._lxcs[key]["status"] = "running"
        self._lxcs[key]["uptime"] = 0
        
        logger.info(f"[MockProxmox] Started LXC {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "start",
            "task": f"UPID:{node}:00000001:00000001:00000001:vzstart:{vmid}:root@pam:",
        }
    
    async def stop_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Stop an LXC container."""
        key = f"{node}:{vmid}"
        if key not in self._lxcs:
            raise ValueError(f"LXC not found: {vmid} on {node}")
        
        self._lxcs[key]["status"] = "stopped"
        self._lxcs[key]["uptime"] = 0
        self._lxcs[key]["cpu"] = 0
        self._lxcs[key]["mem"] = 0
        
        logger.info(f"[MockProxmox] Stopped LXC {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "stop",
            "task": f"UPID:{node}:00000001:00000001:00000001:vzstop:{vmid}:root@pam:",
        }
    
    async def restart_lxc(self, node: str, vmid: int) -> dict[str, Any]:
        """Restart an LXC container."""
        key = f"{node}:{vmid}"
        if key not in self._lxcs:
            raise ValueError(f"LXC not found: {vmid} on {node}")
        
        self._lxcs[key]["status"] = "running"
        self._lxcs[key]["uptime"] = 0
        
        logger.info(f"[MockProxmox] Restarted LXC {vmid} on {node}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "action": "restart",
            "task": f"UPID:{node}:00000001:00000001:00000001:vzreboot:{vmid}:root@pam:",
        }
    
    async def create_snapshot(
        self, 
        node: str, 
        vmid: int, 
        snapname: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a VM snapshot."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        
        if key not in self._snapshots:
            self._snapshots[key] = []
        
        snapshot = {
            "name": snapname,
            "description": description or "",
            "snaptime": int(datetime.now(timezone.utc).timestamp()),
            "vmstate": False,
        }
        self._snapshots[key].append(snapshot)
        
        logger.info(f"[MockProxmox] Created snapshot '{snapname}' for VM {vmid}")
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "snapname": snapname,
            "task": f"UPID:{node}:00000001:00000001:00000001:qmsnapshot:{vmid}:root@pam:",
        }
    
    async def list_snapshots(self, node: str, vmid: int) -> list[dict[str, Any]]:
        """List VM snapshots."""
        key = f"{node}:{vmid}"
        if key not in self._vms:
            raise ValueError(f"VM not found: {vmid} on {node}")
        
        return self._snapshots.get(key, [])
    
    # Additional methods for mock-specific functionality
    def add_vm(self, node: str, vmid: int, data: dict) -> None:
        """Add a mock VM (for test setup)."""
        key = f"{node}:{vmid}"
        self._vms[key] = {"vmid": vmid, "node": node, **data}
    
    def add_lxc(self, node: str, vmid: int, data: dict) -> None:
        """Add a mock LXC (for test setup)."""
        key = f"{node}:{vmid}"
        self._lxcs[key] = {"vmid": vmid, "node": node, **data}
    
    def add_node(self, node: str, data: dict) -> None:
        """Add a mock node (for test setup)."""
        self._nodes[node] = {"node": node, **data}
    
    def reset(self) -> None:
        """Reset to default state."""
        self._setup_defaults()
