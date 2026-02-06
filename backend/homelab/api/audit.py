"""Audit log API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from homelab.storage.database import get_db
from homelab.auth.dependencies import require_permission, CurrentUser
from homelab.auth.models import Permission
from homelab.audit import get_audit_logs, verify_audit_chain, get_audit_stats
from homelab.audit.models import AuditLog


router = APIRouter(prefix="/api/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: str
    sequence: int
    event_type: str
    actor_type: str
    actor_id: str
    resource_type: str
    resource_id: str | None
    action: str
    metadata: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    timestamp: str
    current_hash: str
    previous_hash: str | None


class AuditLogsResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int


class ChainVerificationResponse(BaseModel):
    valid: bool
    total_entries: int
    broken_at_sequence: int | None
    error: str | None


class AuditStatsResponse(BaseModel):
    total_entries: int
    event_types: dict[str, int]
    actor_types: dict[str, int]


@router.get("/logs")
async def list_audit_logs(
    event_type: str | None = Query(None),
    actor_type: str | None = Query(None),
    actor_id: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_permission(Permission.READ_LOGS)),
    db: AsyncSession = Depends(get_db),
) -> AuditLogsResponse:
    """Get audit logs with optional filtering.
    
    Requires READ_LOGS permission.
    """
    logs = await get_audit_logs(
        db,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )
    
    return AuditLogsResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                sequence=log.sequence,
                event_type=log.event_type,
                actor_type=log.actor_type,
                actor_id=log.actor_id,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                action=log.action,
                metadata=log.metadata,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                timestamp=log.timestamp.isoformat(),
                current_hash=log.current_hash,
                previous_hash=log.previous_hash,
            )
            for log in logs
        ],
        total=len(logs),
    )


@router.get("/verify")
async def verify_chain(
    limit: int | None = Query(None, description="Limit verification to N most recent entries"),
    user: CurrentUser = Depends(require_permission(Permission.READ_LOGS)),
    db: AsyncSession = Depends(get_db),
) -> ChainVerificationResponse:
    """Verify integrity of audit log chain.
    
    Requires READ_LOGS permission.
    """
    result = await verify_audit_chain(db, limit=limit)
    
    return ChainVerificationResponse(
        valid=result["valid"],
        total_entries=result["total_entries"],
        broken_at_sequence=result["broken_at_sequence"],
        error=result["error"],
    )


@router.get("/stats")
async def get_stats(
    user: CurrentUser = Depends(require_permission(Permission.READ_LOGS)),
    db: AsyncSession = Depends(get_db),
) -> AuditStatsResponse:
    """Get audit log statistics.
    
    Requires READ_LOGS permission.
    """
    stats = await get_audit_stats(db)
    
    return AuditStatsResponse(
        total_entries=stats["total_entries"],
        event_types=stats["event_types"],
        actor_types=stats["actor_types"],
    )
