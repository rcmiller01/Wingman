"""Audit logging service with hash chain for tamper detection."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.audit.models import AuditLog


def _calculate_hash(log: AuditLog) -> str:
    """Calculate SHA-256 hash of audit log entry.
    
    Hash includes: sequence, event_type, actor_id, action, timestamp, previous_hash
    This creates a chain where each entry depends on the previous one.
    """
    data = (
        f"{log.sequence}:"
        f"{log.event_type}:"
        f"{log.actor_id}:"
        f"{log.action}:"
        f"{log.timestamp.isoformat()}:"
        f"{log.previous_hash or ''}"
    )
    return hashlib.sha256(data.encode()).hexdigest()


async def _get_latest_audit_log(db: AsyncSession) -> AuditLog | None:
    """Get the latest audit log entry by sequence."""
    query = (
        select(AuditLog)
        .order_by(AuditLog.sequence.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_next_sequence(db: AsyncSession) -> int:
    """Get the next sequence number."""
    query = select(func.max(AuditLog.sequence))
    result = await db.execute(query)
    max_seq = result.scalar_one_or_none()
    return (max_seq or 0) + 1


async def log_audit_event(
    db: AsyncSession,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    resource_type: str,
    resource_id: str | None,
    action: str,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Log an audit event with hash chain.
    
    Args:
        db: Database session
        event_type: Type of event (e.g., "user.login", "worker.task.execute")
        actor_type: Type of actor ("user", "worker", "system")
        actor_id: ID of the actor
        resource_type: Type of resource affected (e.g., "session", "task", "config")
        resource_id: ID of the resource (optional)
        action: Action performed (e.g., "create", "update", "delete", "execute")
        metadata: Additional context (optional)
        ip_address: IP address of the actor (optional)
        user_agent: User agent string (optional)
    
    Returns:
        Created audit log entry
    """
    # Get previous log entry
    prev_log = await _get_latest_audit_log(db)
    sequence = await _get_next_sequence(db)
    previous_hash = prev_log.current_hash if prev_log else None
    
    # Create audit log entry
    log = AuditLog(
        sequence=sequence,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
        previous_hash=previous_hash,
        timestamp=datetime.now(timezone.utc),
    )
    
    # Calculate current hash
    log.current_hash = _calculate_hash(log)
    
    db.add(log)
    await db.flush()
    return log


async def verify_audit_chain(db: AsyncSession, *, limit: int | None = None) -> dict[str, Any]:
    """Verify integrity of audit log chain.
    
    Args:
        db: Database session
        limit: Maximum number of entries to verify (None = all)
    
    Returns:
        Verification result with:
        - valid: bool - Whether chain is valid
        - total_entries: int - Total entries checked
        - broken_at_sequence: int | None - Sequence where chain broke (if invalid)
        - error: str | None - Error message (if invalid)
    """
    # Get all audit logs in sequence order
    query = select(AuditLog).order_by(AuditLog.sequence.asc())
    if limit:
        query = query.limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if not logs:
        return {
            "valid": True,
            "total_entries": 0,
            "broken_at_sequence": None,
            "error": None,
        }
    
    valid = True
    broken_at = None
    error = None
    
    for i, log in enumerate(logs):
        # Verify hash
        expected_hash = _calculate_hash(log)
        if log.current_hash != expected_hash:
            valid = False
            broken_at = log.sequence
            error = f"Hash mismatch at sequence {log.sequence}: expected {expected_hash}, got {log.current_hash}"
            break
        
        # Verify chain (except for first entry)
        if i > 0:
            if log.previous_hash != logs[i - 1].current_hash:
                valid = False
                broken_at = log.sequence
                error = f"Chain broken at sequence {log.sequence}: previous_hash does not match previous entry's current_hash"
                break
    
    return {
        "valid": valid,
        "total_entries": len(logs),
        "broken_at_sequence": broken_at,
        "error": error,
    }


async def get_audit_logs(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Get audit logs with optional filtering.
    
    Args:
        db: Database session
        event_type: Filter by event type
        actor_type: Filter by actor type
        actor_id: Filter by actor ID
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        limit: Maximum number of entries to return
        offset: Number of entries to skip
    
    Returns:
        List of audit log entries
    """
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if actor_type:
        query = query.where(AuditLog.actor_type == actor_type)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_audit_stats(db: AsyncSession) -> dict[str, Any]:
    """Get audit log statistics.
    
    Returns:
        Statistics including:
        - total_entries: Total number of audit log entries
        - event_types: Count by event type
        - actor_types: Count by actor type
    """
    # Total entries
    total_query = select(func.count(AuditLog.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    # Count by event type
    event_type_query = (
        select(AuditLog.event_type, func.count(AuditLog.id))
        .group_by(AuditLog.event_type)
        .order_by(func.count(AuditLog.id).desc())
    )
    event_type_result = await db.execute(event_type_query)
    event_types = {row[0]: row[1] for row in event_type_result.all()}
    
    # Count by actor type
    actor_type_query = (
        select(AuditLog.actor_type, func.count(AuditLog.id))
        .group_by(AuditLog.actor_type)
        .order_by(func.count(AuditLog.id).desc())
    )
    actor_type_result = await db.execute(actor_type_query)
    actor_types = {row[0]: row[1] for row in actor_type_result.all()}
    
    return {
        "total_entries": total,
        "event_types": event_types,
        "actor_types": actor_types,
    }
