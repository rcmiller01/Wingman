"""Proxmox adapter for VM/LXC management."""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from homelab.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Thread pool for running sync proxmoxer calls without blocking event loop
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="proxmox")


class ProxmoxAdapter:
    """Adapter for Proxmox API operations."""
    
    def __init__(self):
        self._connected = False
        self.api = None
        self._last_error = None
        
        if settings.proxmox_host and settings.proxmox_user:
            # Parse host and port
            host = settings.proxmox_host.replace("https://", "").replace("http://", "").split(":")[0]
            port = 8006
            if ":" in settings.proxmox_host.replace("https://", "").replace("http://", ""):
                try:
                    port = int(settings.proxmox_host.replace("https://", "").replace("http://", "").split(":")[-1])
                except:
                    pass
            
            logger.info(
                "[ProxmoxAdapter] Initializing connection to %s:%s as %s",
                host,
                port,
                settings.proxmox_user,
            )
            
            try:
                from proxmoxer import ProxmoxAPI
                
                if settings.proxmox_token_name and settings.proxmox_token_value:
                    self.api = ProxmoxAPI(
                        host,
                        port=port,
                        user=settings.proxmox_user,
                        token_name=settings.proxmox_token_name,
                        token_value=settings.proxmox_token_value,
                        verify_ssl=settings.proxmox_verify_ssl,
                        timeout=10
                    )
                    # Try to verify connection immediately
                    try:
                        self.api.nodes.get()
                        self._connected = True
                        logger.info("[ProxmoxAdapter] Connected to Proxmox successfully")
                    except Exception as e:
                        self._last_error = str(e)
                        logger.error("[ProxmoxAdapter] Connection verification failed: %s", e)
                elif settings.proxmox_password:
                    self.api = ProxmoxAPI(
                        host,
                        port=port,
                        user=settings.proxmox_user,
                        password=settings.proxmox_password,
                        verify_ssl=settings.proxmox_verify_ssl,
                        timeout=10
                    )
                    try:
                        self.api.nodes.get()
                        self._connected = True
                        logger.info("[ProxmoxAdapter] Connected to Proxmox successfully")
                    except Exception as e:
                        self._last_error = str(e)
                        logger.error("[ProxmoxAdapter] Connection verification failed: %s", e)
                else:
                    self._last_error = "Missing token name/value or password"
                    logger.error("[ProxmoxAdapter] %s", self._last_error)
            except Exception as e:
                self._last_error = str(e)
                logger.error("[ProxmoxAdapter] Initialization failed: %s", e)

    @property
    def is_connected(self) -> bool:
        # For simplicity in this MVP, we return True if we've ever successfully listed nodes
        # In a real app, we might want periodic health checks
        return self._connected
    
    async def _check_connection(self) -> bool:
        """Verify the connection by attempting to list nodes."""
        if not self.api:
            return False
            
        try:
            # Simple API call to verify credentials
            self.api.nodes.get()
            self._connected = True
            self._last_error = None
            return True
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.error("[ProxmoxAdapter] Connection verification failed: %s", e)
            return False
    
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
            logger.error("[ProxmoxAdapter] Error listing nodes: %s", e)
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
                    logger.error("[ProxmoxAdapter] Error listing VMs on %s: %s", node_name, e)
            
            return vms
        except Exception as e:
            logger.error("[ProxmoxAdapter] Error listing VMs: %s", e)
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
                    logger.error("[ProxmoxAdapter] Error listing LXCs on %s: %s", node_name, e)
            
            return lxcs
        except Exception as e:
            logger.error("[ProxmoxAdapter] Error listing LXCs: %s", e)
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
            logger.error("[ProxmoxAdapter] Error getting status for %s/%s: %s", vmtype, vmid, e)
            return None

    async def start_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Start a VM or LXC. Runs sync API in thread pool to avoid blocking."""
        if not self.api:
            return False
        
        # Validate inputs
        if vmtype not in ("qemu", "lxc"):
            logger.error("[ProxmoxAdapter] Invalid vmtype: %s", vmtype)
            return False
        if not isinstance(vmid, int) or vmid < 0:
            logger.error("[ProxmoxAdapter] Invalid vmid: %s", vmid)
            return False
        
        def _sync_start():
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.start.post()
            else:
                self.api.nodes(node).lxc(vmid).status.start.post()
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, _sync_start)
            return True
        except Exception as e:
            logger.error("[ProxmoxAdapter] Error starting %s/%s: %s", vmtype, vmid, e)
            return False

    async def stop_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Stop a VM or LXC (shutdown). Runs sync API in thread pool."""
        if not self.api:
            return False
        
        # Validate inputs
        if vmtype not in ("qemu", "lxc"):
            logger.error("[ProxmoxAdapter] Invalid vmtype: %s", vmtype)
            return False
        if not isinstance(vmid, int) or vmid < 0:
            logger.error("[ProxmoxAdapter] Invalid vmid: %s", vmid)
            return False
        
        def _sync_stop():
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.shutdown.post()
            else:
                self.api.nodes(node).lxc(vmid).status.shutdown.post()
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, _sync_stop)
            return True
        except Exception as e:
            logger.error("[ProxmoxAdapter] Error stopping %s/%s: %s", vmtype, vmid, e)
            return False

    async def reboot_resource(self, node: str, vmtype: str, vmid: int) -> bool:
        """Reboot/Restart a VM or LXC. Runs sync API in thread pool."""
        if not self.api:
            return False
        
        # Validate inputs
        if vmtype not in ("qemu", "lxc"):
            logger.error("[ProxmoxAdapter] Invalid vmtype: %s", vmtype)
            return False
        if not isinstance(vmid, int) or vmid < 0:
            logger.error("[ProxmoxAdapter] Invalid vmid: %s", vmid)
            return False
        
        def _sync_reboot():
            if vmtype == "qemu":
                self.api.nodes(node).qemu(vmid).status.reboot.post()
            else:
                self.api.nodes(node).lxc(vmid).status.reboot.post()
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, _sync_reboot)
            return True
        except Exception as e:
            logger.error("[ProxmoxAdapter] Error rebooting %s/%s: %s", vmtype, vmid, e)
            return False
            return False


# Singleton instance
proxmox_adapter = ProxmoxAdapter()
