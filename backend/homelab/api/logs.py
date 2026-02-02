"""Logs API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from homelab.storage import get_db
from homelab.collectors import log_collector
from homelab.storage.models import FileLogSource
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


class FileLogSourceResponse(BaseModel):
    id: str
    name: str
    path: str
    resource_ref: str
    enabled: bool
    retention_days: int
    last_position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileLogSourceCreate(BaseModel):
    name: str
    path: str
    resource_ref: str
    enabled: bool | None = None
    retention_days: int | None = None


class FileLogSourceUpdate(BaseModel):
    name: str | None = None
    path: str | None = None
    resource_ref: str | None = None
    enabled: bool | None = None
    retention_days: int | None = None


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


@router.get("/file-sources")
async def list_file_sources(
    db: AsyncSession = Depends(get_db),
):
    """List configured file log sources."""
    result = await db.execute(select(FileLogSource).order_by(FileLogSource.created_at.desc()))
    sources = result.scalars().all()
    return {
        "count": len(sources),
        "sources": [FileLogSourceResponse.model_validate(source) for source in sources],
    }


@router.post("/file-sources")
async def add_file_source(
    payload: FileLogSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new file log source (disabled by default)."""
    source = FileLogSource(
        name=payload.name,
        path=payload.path,
        resource_ref=payload.resource_ref,
        enabled=payload.enabled if payload.enabled is not None else False,
        retention_days=payload.retention_days or 90,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return FileLogSourceResponse.model_validate(source)


@router.patch("/file-sources/{source_id}")
async def update_file_source(
    source_id: str,
    payload: FileLogSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a file log source configuration."""
    result = await db.execute(select(FileLogSource).where(FileLogSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        return {"error": "File log source not found"}

    if payload.name is not None:
        source.name = payload.name
    if payload.path is not None:
        source.path = payload.path
    if payload.resource_ref is not None:
        source.resource_ref = payload.resource_ref
    if payload.enabled is not None:
        source.enabled = payload.enabled
    if payload.retention_days is not None:
        source.retention_days = payload.retention_days

    await db.commit()
    await db.refresh(source)
    return FileLogSourceResponse.model_validate(source)


@router.delete("/file-sources/{source_id}")
async def remove_file_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a file log source."""
    result = await db.execute(select(FileLogSource).where(FileLogSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        return {"error": "File log source not found"}

    await db.delete(source)
    await db.commit()
    return {"deleted": True, "source_id": source_id}
