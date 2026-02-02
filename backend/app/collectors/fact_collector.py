"""Fact Collector - collects normalized observations from adapters."""

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.storage.models import Fact
from app.adapters import docker_adapter, proxmox_adapter


class FactCollector:
    """Collects and stores normalized facts from infrastructure adapters."""
    
    async def collect_all(self, db: AsyncSession) -> dict[str, int]:
        """Collect facts from all adapters."""
        counts = {
            "docker": 0,
            "proxmox": 0,
        }
        
        counts["docker"] = await self.collect_docker_facts(db)
        counts["proxmox"] = await self.collect_proxmox_facts(db)
        
        return counts
    
    async def collect_docker_facts(self, db: AsyncSession) -> int:
        """Collect facts from Docker containers."""
        if not docker_adapter.is_connected:
            return 0
        
        containers = await docker_adapter.list_containers(all=True)
        count = 0
        
        for container in containers:
            # Container status fact (Observation only)
            await self._store_fact(
                db,
                resource_ref=container["resource_ref"],
                fact_type="container_status",
                value={
                    "status": container["status"],
                    "restart_count": container["restart_count"],
                    "health": container.get("health"),
                    "image": container["image"],
                    "name": container["name"],
                },
                source="docker",
            )
            count += 1
        
        return count
    
    async def collect_proxmox_facts(self, db: AsyncSession) -> int:
        """Collect facts from Proxmox nodes, VMs, and LXCs."""
        if not proxmox_adapter.is_connected:
            return 0
        
        count = 0
        
        # Collect node facts
        nodes = await proxmox_adapter.list_nodes()
        for node in nodes:
            await self._store_fact(
                db,
                resource_ref=node["resource_ref"],
                fact_type="node_status",
                value={
                    "status": node["status"],
                    "cpu": node.get("cpu"),
                    "mem": node.get("mem"),
                    "maxmem": node.get("maxmem"),
                    "uptime": node.get("uptime"),
                },
                source="proxmox",
            )
            count += 1
        
        # Collect VM facts
        vms = await proxmox_adapter.list_vms()
        for vm in vms:
            await self._store_fact(
                db,
                resource_ref=vm["resource_ref"],
                fact_type="vm_status",
                value={
                    "status": vm["status"],
                    "name": vm["name"],
                    "node": vm["node"],
                    "cpu": vm.get("cpu"),
                    "mem": vm.get("mem"),
                    "uptime": vm.get("uptime"),
                },
                source="proxmox",
            )
            count += 1
        
        # Collect LXC facts
        lxcs = await proxmox_adapter.list_lxcs()
        for lxc in lxcs:
            await self._store_fact(
                db,
                resource_ref=lxc["resource_ref"],
                fact_type="lxc_status",
                value={
                    "status": lxc["status"],
                    "name": lxc["name"],
                    "node": lxc["node"],
                    "cpu": lxc.get("cpu"),
                    "mem": lxc.get("mem"),
                    "uptime": lxc.get("uptime"),
                },
                source="proxmox",
            )
            count += 1
        
        return count
    
    async def get_recent_facts(
        self, 
        db: AsyncSession, 
        resource_ref: str | None = None,
        fact_type: str | None = None,
        hours: int = 24,
    ) -> list[Fact]:
        """Get recent facts, optionally filtered."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(Fact).where(Fact.timestamp >= since)
        
        if resource_ref:
            query = query.where(Fact.resource_ref == resource_ref)
        if fact_type:
            query = query.where(Fact.fact_type == fact_type)
        
        query = query.order_by(Fact.timestamp.desc()).limit(100)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _store_fact(
        self,
        db: AsyncSession,
        resource_ref: str,
        fact_type: str,
        value: dict[str, Any],
        source: str,
    ) -> Fact:
        """Store a new fact in the database."""
        fact = Fact(
            resource_ref=resource_ref,
            fact_type=fact_type,
            value=value,
            source=source,
            timestamp=datetime.utcnow(),
        )
        db.add(fact)
        return fact


# Singleton
fact_collector = FactCollector()
