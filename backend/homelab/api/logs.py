"""Logs API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from homelab.storage import get_db
from homelab.collectors import log_collector
from homelab.adapters import docker_adapter

router = APIRouter(prefix="/api/logs", tags=["logs"])


class LogEntryResponse(BaseModel):
    """Log entry response model."""
    id: str
    resource_ref: str
    log_source: str
    content: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


@router.get("/container/{container_id}")
async def get_container_logs(
    container_id: str,
    limit: int = Query(100, le=500),
    since_hours: int | None = Query(None, le=168),  # Max 7 days
    db: AsyncSession = Depends(get_db),
):
    """Get stored logs for a container."""
    # Resolve container to resource_ref
    container = await docker_adapter.get_container(container_id)
    if not container:
        return {"error": "Container not found", "logs": []}
    
    logs = await log_collector.get_logs(
        db,
        resource_ref=container["resource_ref"],
        limit=limit,
        since_hours=since_hours,
    )
    
    return {
        "container": container["name"],
        "resource_ref": container["resource_ref"],
        "count": len(logs),
        "logs": [LogEntryResponse.model_validate(log) for log in logs],
    }


@router.get("/container/{container_id}/errors")
async def get_container_errors(
    container_id: str,
    hours: int = Query(24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Extract error patterns from container logs."""
    container = await docker_adapter.get_container(container_id)
    if not container:
        return {"error": "Container not found", "patterns": []}
    
    patterns = await log_collector.extract_error_signatures(
        db,
        resource_ref=container["resource_ref"],
        hours=hours,
    )
    
    return {
        "container": container["name"],
        "resource_ref": container["resource_ref"],
        "error_count": len(patterns),
        "patterns": patterns,
    }


@router.post("/collect/{container_id}")
async def collect_container_logs(
    container_id: str,
    since_minutes: int = Query(60, le=1440),  # Max 24 hours
    db: AsyncSession = Depends(get_db),
):
    """Trigger log collection for a specific container."""
    count = await log_collector.collect_container_logs(
        db,
        container_id=container_id,
        since_minutes=since_minutes,
    )
    await db.commit()
    
    return {
        "container_id": container_id,
        "logs_collected": count,
    }


@router.post("/collect")
async def collect_all_logs(
    since_minutes: int = Query(60, le=1440),
    db: AsyncSession = Depends(get_db),
):
    """Trigger log collection for all running containers."""
    results = await log_collector.collect_all_container_logs(
        db,
        since_minutes=since_minutes,
    )
    await db.commit()
    
    return {
        "containers": results,
        "total_logs": sum(results.values()),
    }
