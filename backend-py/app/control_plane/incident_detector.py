"""Incident Detector - detects issues from facts and logs."""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from app.storage.models import Fact, Incident, IncidentNarrative, IncidentSeverity, IncidentStatus
from app.collectors import log_collector
from app.notifications.webhook import notifier


# Detection thresholds
RESTART_LOOP_THRESHOLD = 3  # Restarts to trigger incident
ERROR_REPEAT_THRESHOLD = 5  # Repeated errors to trigger incident
ERROR_WINDOW_HOURS = 1      # Time window for error counting


class IncidentDetector:
    """Detects incidents from collected facts and logs."""
    
    async def detect_all(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Run all detection rules and return new incidents."""
        detected = []
        
        # Check for restart loops
        restart_incidents = await self._detect_restart_loops(db)
        detected.extend(restart_incidents)
        
        # Check for repeated errors
        error_incidents = await self._detect_error_patterns(db)
        detected.extend(error_incidents)
        
        return detected
    
    async def _detect_restart_loops(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect containers with excessive restarts."""
        # Get recent restart_loop_detected facts
        since = datetime.utcnow() - timedelta(hours=1)
        
        result = await db.execute(
            select(Fact)
            .where(Fact.fact_type == "restart_loop_detected")
            .where(Fact.timestamp >= since)
        )
        facts = list(result.scalars().all())
        
        incidents = []
        for fact in facts:
            # Check if incident already exists for this resource
            existing = await self._get_open_incident(db, fact.resource_ref)
            if existing:
                continue  # Already tracking this
            
            restart_count = fact.value.get("restart_count", 0)
            container_name = fact.value.get("container_name", "unknown")
            
            # Create incident
            incident = await self._create_incident(
                db,
                severity=IncidentSeverity.high if restart_count > 5 else IncidentSeverity.medium,
                affected_resources=[fact.resource_ref],
                symptoms=[
                    f"Container {container_name} has restarted {restart_count} times",
                    f"Restart loop detected at {fact.timestamp.isoformat()}",
                ],
                summary=f"Restart loop detected: {container_name}",
            )
            
            incidents.append({
                "incident_id": incident.id,
                "type": "restart_loop",
                "resource": fact.resource_ref,
                "details": fact.value,
            })
        
        return incidents
    
    async def _detect_error_patterns(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect repeated error patterns in logs."""
        # Get container status facts to know which containers to check
        result = await db.execute(
            select(Fact)
            .where(Fact.fact_type == "container_status")
            .where(Fact.timestamp >= datetime.utcnow() - timedelta(hours=1))
        )
        container_facts = list(result.scalars().all())
        
        incidents = []
        for fact in container_facts:
            resource_ref = fact.resource_ref
            
            # Check if incident already exists
            existing = await self._get_open_incident(db, resource_ref)
            if existing:
                continue
            
            # Extract error signatures
            errors = await log_collector.extract_error_signatures(
                db, resource_ref, hours=ERROR_WINDOW_HOURS
            )
            
            if len(errors) >= ERROR_REPEAT_THRESHOLD:
                container_name = fact.value.get("name", "unknown")
                
                # Get unique error keywords
                keywords = set(e["keyword"] for e in errors)
                
                incident = await self._create_incident(
                    db,
                    severity=IncidentSeverity.medium,
                    affected_resources=[resource_ref],
                    symptoms=[
                        f"Container {container_name} has {len(errors)} errors in the last hour",
                        f"Error types: {', '.join(keywords)}",
                        f"Sample: {errors[0]['content'][:100]}...",
                    ],
                    summary=f"Repeated errors in {container_name}",
                )
                
                incidents.append({
                    "incident_id": incident.id,
                    "type": "error_pattern",
                    "resource": resource_ref,
                    "error_count": len(errors),
                    "keywords": list(keywords),
                })
        
        return incidents
    
    async def _get_open_incident(
        self, 
        db: AsyncSession, 
        resource_ref: str
    ) -> Incident | None:
        """Check if there's already an open incident for this resource."""
        result = await db.execute(
            select(Incident)
            .where(Incident.status.in_([IncidentStatus.open, IncidentStatus.investigating]))
            .where(Incident.affected_resources.contains([resource_ref]))
        )
        return result.scalars().first()
    
    async def _create_incident(
        self,
        db: AsyncSession,
        severity: IncidentSeverity,
        affected_resources: list[str],
        symptoms: list[str],
        summary: str,
    ) -> Incident:
        """Create a new incident with narrative placeholder."""
        incident = Incident(
            severity=severity,
            status=IncidentStatus.open,
            affected_resources=affected_resources,
            symptoms=symptoms,
            detected_at=datetime.utcnow(),
        )
        db.add(incident)
        await db.flush()  # Get the ID
        
        # Create narrative placeholder
        narrative = IncidentNarrative(
            incident_id=incident.id,
            time_range={"start": datetime.utcnow().isoformat(), "end": None},
            narrative_text=f"## {summary}\n\n**Symptoms:**\n" + "\n".join(f"- {s}" for s in symptoms) + "\n\n*Analysis pending...*",
            evidence_refs=[],
            resolution_steps=[],
        )
        db.add(narrative)
        
        print(f"[IncidentDetector] Created incident {incident.id}: {summary}")
        
        # Trigger notification
        import asyncio
        asyncio.create_task(notifier.notify("incident.created", {
            "incident_id": incident.id,
            "severity": severity.value,
            "summary": summary,
            "affected_resources": affected_resources
        }))
        
        return incident


# Singleton
incident_detector = IncidentDetector()
