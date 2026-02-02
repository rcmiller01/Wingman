"""Incidents API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Any

from homelab.storage import get_db
from homelab.storage.models import Incident, IncidentNarrative, IncidentStatus, IncidentSeverity
from homelab.control_plane import incident_detector, narrative_generator
from homelab.notifications.router import notification_router

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class IncidentResponse(BaseModel):
    """Incident response model."""
    id: str
    severity: str
    status: str
    affected_resources: list[str]
    symptoms: list[str]
    detected_at: datetime
    resolved_at: datetime | None
    
    class Config:
        from_attributes = True


class NarrativeResponse(BaseModel):
    """Narrative response model."""
    id: str
    incident_id: str
    narrative_text: str
    root_cause_hypothesis: str | None
    confidence: float | None
    resolution_steps: list[str]
    
    class Config:
        from_attributes = True


@router.get("")
async def list_incidents(
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List incidents, optionally filtered."""
    query = select(Incident, IncidentNarrative).outerjoin(IncidentNarrative)

    if status and status != "all":
        try:
            status_enum = IncidentStatus[status]
            query = query.where(Incident.status == status_enum)
        except KeyError:
            raise HTTPException(400, f"Invalid status: {status}")
    
    if severity:
        try:
            severity_enum = IncidentSeverity[severity]
            query = query.where(Incident.severity == severity_enum)
        except KeyError:
            raise HTTPException(400, f"Invalid severity: {severity}")
    
    query = query.order_by(Incident.detected_at.desc()).limit(limit)
    
    result = await db.execute(query)
    incidents = list(result.all())
    
    return {
        "count": len(incidents),
        "incidents": [
            {
                "id": str(incident.id),
                "severity": incident.severity.value,
                "status": incident.status.value,
                "affected_resources": incident.affected_resources,
                "symptoms": incident.symptoms,
                "detected_at": incident.detected_at,
                "resolved_at": incident.resolved_at,
                "narrative": {
                    "narrative_text": narrative.narrative_text,
                } if narrative else None,
            }
            for incident, narrative in incidents
        ],
    }


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific incident with its narrative."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(404, "Incident not found")
    
    # Get narrative
    result = await db.execute(
        select(IncidentNarrative).where(IncidentNarrative.incident_id == incident_id)
    )
    narrative = result.scalars().first()
    
    return {
        "incident": {
            "id": str(incident.id),
            "severity": incident.severity.value,
            "status": incident.status.value,
            "affected_resources": incident.affected_resources,
            "symptoms": incident.symptoms,
            "detected_at": incident.detected_at,
            "resolved_at": incident.resolved_at,
        },
        "narrative": {
            "narrative_text": narrative.narrative_text if narrative else None,
            "root_cause": narrative.root_cause_hypothesis if narrative else None,
            "confidence": narrative.confidence if narrative else None,
            "resolution_steps": narrative.resolution_steps if narrative else [],
        } if narrative else None,
    }


@router.post("/{incident_id}/analyze")
async def analyze_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger LLM analysis for an incident."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(404, "Incident not found")
    
    # Generate narrative
    narrative_text = await narrative_generator.generate_narrative(db, incident)
    
    # Update narrative in DB
    await narrative_generator.update_incident_narrative(
        db, 
        incident_id, 
        narrative_text,
    )
    await db.commit()
    
    return {
        "incident_id": incident_id,
        "narrative": narrative_text,
    }


@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark an incident as resolved."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(404, "Incident not found")
    
    incident.status = IncidentStatus.resolved
    incident.resolved_at = datetime.utcnow()
    await db.commit()

    await notification_router.notify_event(
        "incident_resolved",
        {
            "incident_id": str(incident.id),
            "severity": incident.severity.value,
            "status": incident.status.value,
            "resolved_at": incident.resolved_at.isoformat(),
            "affected_resources": incident.affected_resources,
        },
        severity=incident.severity.value,
        tags=["incident"],
    )
    
    return {
        "incident_id": incident_id,
        "status": "resolved",
        "resolved_at": incident.resolved_at,
    }


@router.post("/detect")
async def run_detection(db: AsyncSession = Depends(get_db)):
    """Manually trigger incident detection."""
    detected = await incident_detector.detect_all(db)
    await db.commit()
    
    return {
        "detected_count": len(detected),
        "incidents": detected,
    }
