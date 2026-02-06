"""Cross-site incident detection and correlation."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import select, Index, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from homelab.storage.models import Base, String, Text, JSON, DateTime


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Incident(Base):
    """Cross-site incident tracking and correlation."""
    
    __tablename__ = "incidents"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[IncidentSeverity] = mapped_column(String(20), nullable=False, index=True)
    
    # Site tracking
    site_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    affected_sites: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Correlation
    correlation_group: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_incidents_site_severity", "site_name", "severity"),
        Index("ix_incidents_correlation", "correlation_group"),
    )


async def correlate_incidents(
    db: AsyncSession,
    *,
    time_window: timedelta = timedelta(minutes=15),
    similarity_threshold: float = 0.7,
) -> list[str]:
    """Correlate incidents across sites.
    
    Finds similar incidents within a time window and groups them by correlation_group.
    
    Args:
        db: Database session
        time_window: Time window to consider for correlation
        similarity_threshold: Minimum similarity score (0.0 to 1.0)
    
    Returns:
        List of correlation group IDs that were updated
    """
    cutoff = datetime.now(timezone.utc) - time_window
    
    # Get uncorrelated incidents
    query = (
        select(Incident)
        .where(
            Incident.detected_at >= cutoff,
            Incident.correlation_group.is_(None),
            Incident.resolved_at.is_(None),
        )
        .order_by(Incident.detected_at.desc())
    )
    
    result = await db.execute(query)
    incidents = result.scalars().all()
    
    correlation_groups = []
    
    for incident in incidents:
        # Find similar incidents
        similar = await _find_similar_incidents(
            db,
            incident=incident,
            threshold=similarity_threshold,
            time_window=time_window,
        )
        
        if similar:
            # Create or join correlation group
            group_id = similar[0].correlation_group or str(uuid4())
            incident.correlation_group = group_id
            
            # Update affected_sites
            all_sites = {incident.site_name}
            for sim in similar:
                sim.correlation_group = group_id
                all_sites.add(sim.site_name)
            
            # Update all incidents in group with affected_sites
            for inc in [incident] + similar:
                inc.affected_sites = sorted(list(all_sites))
            
            correlation_groups.append(group_id)
    
    await db.flush()
    return correlation_groups


async def _find_similar_incidents(
    db: AsyncSession,
    *,
    incident: Incident,
    threshold: float,
    time_window: timedelta,
) -> list[Incident]:
    """Find similar incidents using type and metadata matching."""
    cutoff = incident.detected_at - time_window
    
    query = (
        select(Incident)
        .where(
            Incident.id != incident.id,
            Incident.incident_type == incident.incident_type,
            Incident.detected_at >= cutoff,
            Incident.resolved_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    candidates = result.scalars().all()
    
    # Simple similarity: same type + overlapping metadata keys
    similar = []
    for candidate in candidates:
        score = _calculate_similarity(incident.metadata, candidate.metadata)
        if score >= threshold:
            similar.append(candidate)
    
    return similar


def _calculate_similarity(meta1: dict, meta2: dict) -> float:
    """Calculate metadata similarity score (0.0 to 1.0)."""
    keys1 = set(meta1.keys())
    keys2 = set(meta2.keys())
    
    if not keys1 and not keys2:
        return 1.0
    
    intersection = keys1 & keys2
    union = keys1 | keys2
    
    return len(intersection) / len(union) if union else 0.0


async def create_incident(
    db: AsyncSession,
    *,
    incident_type: str,
    severity: IncidentSeverity,
    site_name: str,
    title: str,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> Incident:
    """Create a new incident.
    
    Args:
        db: Database session
        incident_type: Type of incident (e.g., 'service_down', 'high_cpu', 'disk_full')
        severity: Incident severity
        site_name: Site where incident was detected
        title: Short incident title
        description: Detailed description
        metadata: Additional metadata for correlation
    
    Returns:
        Created incident
    """
    incident = Incident(
        incident_type=incident_type,
        severity=severity,
        site_name=site_name,
        title=title,
        description=description,
        metadata=metadata or {},
    )
    db.add(incident)
    await db.flush()
    return incident


async def get_correlated_incidents(
    db: AsyncSession,
    *,
    correlation_group: str,
) -> list[Incident]:
    """Get all incidents in a correlation group.
    
    Args:
        db: Database session
        correlation_group: Correlation group ID
    
    Returns:
        List of incidents in the group
    """
    query = (
        select(Incident)
        .where(Incident.correlation_group == correlation_group)
        .order_by(Incident.detected_at.asc())
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def resolve_incident(
    db: AsyncSession,
    *,
    incident_id: str,
    resolve_group: bool = False,
) -> int:
    """Resolve an incident.
    
    Args:
        db: Database session
        incident_id: Incident ID to resolve
        resolve_group: If True, resolve all incidents in the correlation group
    
    Returns:
        Number of incidents resolved
    """
    incident = await db.get(Incident, incident_id)
    if not incident:
        return 0
    
    now = datetime.now(timezone.utc)
    count = 0
    
    if resolve_group and incident.correlation_group:
        # Resolve all incidents in the group
        query = (
            select(Incident)
            .where(
                Incident.correlation_group == incident.correlation_group,
                Incident.resolved_at.is_(None),
            )
        )
        result = await db.execute(query)
        incidents = result.scalars().all()
        
        for inc in incidents:
            inc.resolved_at = now
            count += 1
    else:
        # Resolve only this incident
        incident.resolved_at = now
        count = 1
    
    await db.flush()
    return count
