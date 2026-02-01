"""Proxmox adapter for VM/LXC management."""

from typing import Any
from app.config import get_settings

settings = get_settings()


class ProxmoxAdapter:
    """Adapter for Proxmox API operations."""
    
    def __init__(self):
        self._connected = False
        self.api = None
        
        if settings.proxmox_host and settings.proxmox_user:
            try:
                from proxmoxer import ProxmoxAPI
                self.api = ProxmoxAPI(
                    settings.proxmox_host,
                    user=settings.proxmox_user,
                    token_name=settings.proxmox_token_name,
                    token_value=settings.proxmox_token_value,
                    verify_ssl=settings.proxmox_verify_ssl,
                )
                self._connected = True
                print("[ProxmoxAdapter] Connected successfully")
            except Exception as e:
                print(f"[ProxmoxAdapter] Failed to connect: {e}")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def list_nodes(self) -> list[dict[str, Any]]:
        """List all Proxmox nodes."""
        if not self.api:
            return []
        
        try:
            nodes = self.api.nodes.get()
            return [
                {
                    "name": n["node"],
                    "status": n.get("status", "unknown"),
                    "cpu": n.get("cpu"),
                    "mem": n.get("mem"),
                    "maxmem": n.get("maxmem"),
                    "uptime": n.get("uptime"),
                    "resource_ref": f"proxmox://node/{n['node']}",
                }
                for n in nodes
            ]
        except Exception as e:
            print(f"[ProxmoxAdapter] Error listing nodes: {e}")
            return []
    
    async def list_vms(self, node: str | None = None) -> list[dict[str, Any]]:
        """List all VMs across nodes or on a specific node."""
        if not self.api:
            return []
        
        try:
            vms = []
            nodes = [{"node": node}] if node else self.api.nodes.get()
            
            for n in nodes:
                node_name = n["node"]
                try:
                    node_vms = self.api.nodes(node_name).qemu.get()
                    for vm in node_vms:
                        vms.append({
                            "vmid": vm["vmid"],
                            "name": vm.get("name", f"vm-{vm['vmid']}"),
                            "status": vm.get("status", "unknown"),
                            "node": node_name,
                            "type": "qemu",
                            "cpu": vm.get("cpu"),
                            "mem": vm.get("mem"),
                            "maxmem": vm.get("maxmem"),
                            "uptime": vm.get("uptime"),
                            "resource_ref": f"proxmox://{node_name}/qemu/{vm['vmid']}",
                        })
                except Exception as e:
                    print(f"[ProxmoxAdapter] Error listing VMs on {node_name}: {e}")
            
            return vms
        except Exception as e:
            print(f"[ProxmoxAdapter] Error listing VMs: {e}")
            return []
    
    async def list_lxcs(self, node: str | None = None) -> list[dict[str, Any]]:
        """List all LXC containers across nodes or on a specific node."""
        if not self.api:
            return []
        
        try:
            lxcs = []
            nodes = [{"node": node}] if node else self.api.nodes.get()
            
            for n in nodes:
                node_name = n["node"]
                try:
                    node_lxcs = self.api.nodes(node_name).lxc.get()
                    for lxc in node_lxcs:
                        lxcs.append({
                            "vmid": lxc["vmid"],
                            "name": lxc.get("name", f"ct-{lxc['vmid']}"),
                            "status": lxc.get("status", "unknown"),
                            "node": node_name,
                            "type": "lxc",
                            "cpu": lxc.get("cpu"),
                            "mem": lxc.get("mem"),
                            "maxmem": lxc.get("maxmem"),
                            "uptime": lxc.get("uptime"),
                            "resource_ref": f"proxmox://{node_name}/lxc/{lxc['vmid']}",
                        })
                except Exception as e:
                    print(f"[ProxmoxAdapter] Error listing LXCs on {node_name}: {e}")
            
            return lxcs
        except Exception as e:
            print(f"[ProxmoxAdapter] Error listing LXCs: {e}")
            return []
    
    async def get_resource_status(self, node: str, vmtype: str, vmid: int) -> dict[str, Any] | None:
        """Get status of a specific VM or LXC."""
        if not self.api:
            return None
        
        try:
            if vmtype == "qemu":
                status = self.api.nodes(node).qemu(vmid).status.current.get()
            elif vmtype == "lxc":
                status = self.api.nodes(node).lxc(vmid).status.current.get()
            else:
                return None
            
            return {
                "vmid": vmid,
                "name": status.get("name"),
                "status": status.get("status"),
                "cpu": status.get("cpu"),
                "mem": status.get("mem"),
                "maxmem": status.get("maxmem"),
                "uptime": status.get("uptime"),
            }
        except Exception as e:
            print(f"[ProxmoxAdapter] Error getting status for {vmtype}/{vmid}: {e}")
            return None

    async def start_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Start a VM or LXC."""
        if not self.api:
            return False
        
        try:
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.start.post()
            elif vmtype == "lxc":
                self.api.nodes(node).lxc(vmid).status.start.post()
            else:
                return False
            return True
        except Exception as e:
            print(f"[ProxmoxAdapter] Error starting {vmtype}/{vmid}: {e}")
            return False

    async def stop_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Stop a VM or LXC (shutdown)."""
        if not self.api:
            return False
        
        try:
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.shutdown.post()
            elif vmtype == "lxc":
                self.api.nodes(node).lxc(vmid).status.shutdown.post()
            else:
                return False
            return True
        except Exception as e:
            print(f"[ProxmoxAdapter] Error stopping {vmtype}/{vmid}: {e}")
            return False

    async def reboot_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Reboot/Restart a VM or LXC."""
        if not self.api:
            return False
        
        try:
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.reboot.post()
            elif vmtype == "lxc":
                self.api.nodes(node).lxc(vmid).status.reboot.post()
            else:
                return False
            return True
        except Exception as e:
            print(f"[ProxmoxAdapter] Error rebooting {vmtype}/{vmid}: {e}")
            return False


# Singleton instance
proxmox_adapter = ProxmoxAdapter()
