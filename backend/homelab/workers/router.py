"""Worker task routing by site and capabilities."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import WorkerNode, WorkerStatus, WorkerTask, WorkerTaskStatus
from datetime import datetime, timezone


async def find_available_worker(
    db: AsyncSession,
    *,
    site_name: str,
    required_capabilities: dict[str, Any] | None = None,
) -> str | None:
    """Find an available worker for the given site and capabilities.
    
    Args:
        db: Database session
        site_name: Site name to find worker in
        required_capabilities: Required worker capabilities (e.g., {"docker": True})
    
    Returns:
        Worker ID if found, None otherwise
    """
    
    query = (
        select(WorkerNode)
        .where(
            WorkerNode.site_name == site_name,
            WorkerNode.status == WorkerStatus.online,
        )
    )
    
    result = await db.execute(query)
    workers = result.scalars().all()
    
    if not workers:
        return None
    
    # Filter by capabilities
    if required_capabilities:
        workers = [
            w for w in workers
            if _capabilities_match(w.capabilities, required_capabilities)
        ]
    
    if not workers:
        return None
    
    # Return worker with least load (simple round-robin for now)
    # TODO: Implement proper load balancing based on active task count
    return workers[0].worker_id


def _capabilities_match(worker_caps: dict[str, Any], required_caps: dict[str, Any]) -> bool:
    """Check if worker has all required capabilities.
    
    Args:
        worker_caps: Worker's declared capabilities
        required_caps: Required capabilities for the task
    
    Returns:
        True if worker has all required capabilities
    """
    for key, required_value in required_caps.items():
        if key not in worker_caps:
            return False
        
        # Handle boolean capabilities
        if isinstance(required_value, bool):
            if worker_caps[key] != required_value:
                return False
        # Handle string/numeric capabilities
        elif worker_caps[key] != required_value:
            return False
    
    return True


async def route_task_to_worker(
    db: AsyncSession,
    *,
    task_type: str,
    site_name: str | None = None,
    required_capabilities: dict[str, Any] | None = None,
    payload: dict[str, Any],
    timeout_seconds: int = 60,
    max_attempts: int = 3,
) -> str | None:
    """Route a task to an appropriate worker.
    
    This is a high-level routing function that:
    1. Finds an available worker matching site and capabilities
    2. Enqueues the task for that worker
    
    Args:
        db: Database session
        task_type: Type of task to route
        site_name: Preferred site (None = any site)
        required_capabilities: Required worker capabilities
        payload: Task payload
        timeout_seconds: Task timeout
        max_attempts: Maximum retry attempts
    
    Returns:
        Worker ID that task was routed to, or None if no worker available
    """
    from homelab.workers.service import enqueue_worker_task
    
    # Find available worker
    target_site = site_name or "any"
    worker_id = await find_available_worker(
        db,
        site_name=target_site,
        required_capabilities=required_capabilities,
    )
    
    if not worker_id:
        return None
    
    # Enqueue task for this worker
    await enqueue_worker_task(
        db,
        task_type=task_type,
        worker_id=worker_id,
        idempotency_key=f"{task_type}:{worker_id}:{datetime.now(timezone.utc).timestamp()}",
        payload=payload,
        timeout_seconds=timeout_seconds,
        site_name=target_site,
        max_attempts=max_attempts,
    )
    
    return worker_id


async def get_worker_load(
    db: AsyncSession,
    *,
    worker_id: str,
) -> dict[str, Any]:
    """Get current load metrics for a worker.
    
    Args:
        db: Database session
        worker_id: Worker ID
    
    Returns:
        Load metrics including active task count, queued task count, etc.
    """
    # Count active tasks
    active_query = (
        select(WorkerTask)
        .where(
            WorkerTask.worker_id == worker_id,
            WorkerTask.status.in_([WorkerTaskStatus.claimed, WorkerTaskStatus.running]),
        )
    )
    active_result = await db.execute(active_query)
    active_count = len(list(active_result.scalars().all()))
    
    # Count queued tasks
    queued_query = (
        select(WorkerTask)
        .where(
            WorkerTask.worker_id == worker_id,
            WorkerTask.status == WorkerTaskStatus.queued,
        )
    )
    queued_result = await db.execute(queued_query)
    queued_count = len(list(queued_result.scalars().all()))
    
    return {
        "worker_id": worker_id,
        "active_tasks": active_count,
        "queued_tasks": queued_count,
        "total_load": active_count + queued_count,
    }


async def balance_load_across_site(
    db: AsyncSession,
    *,
    site_name: str,
) -> dict[str, Any]:
    """Get load distribution across all workers in a site.
    
    Args:
        db: Database session
        site_name: Site name
    
    Returns:
        Load distribution metrics
    """
    # Get all workers in site
    query = (
        select(WorkerNode)
        .where(
            WorkerNode.site_name == site_name,
            WorkerNode.status == WorkerStatus.online,
        )
    )
    result = await db.execute(query)
    workers = result.scalars().all()
    
    if not workers:
        return {
            "site_name": site_name,
            "worker_count": 0,
            "total_load": 0,
            "workers": [],
        }
    
    # Get load for each worker
    worker_loads = []
    total_load = 0
    
    for worker in workers:
        load = await get_worker_load(db, worker_id=worker.worker_id)
        worker_loads.append(load)
        total_load += load["total_load"]
    
    return {
        "site_name": site_name,
        "worker_count": len(workers),
        "total_load": total_load,
        "average_load": total_load / len(workers) if workers else 0,
        "workers": worker_loads,
    }
