"""Incident Detector - detects issues from facts and logs."""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from homelab.storage.models import (
    Fact,
    Incident,
    IncidentNarrative,
    IncidentSeverity,
    IncidentStatus,
    FileLogSource,
)
from homelab.collectors import log_collector
from homelab.notifications.router import notification_router


# Detection thresholds
RESTART_LOOP_THRESHOLD = 3  # Restarts to trigger incident
ERROR_REPEAT_THRESHOLD = 5  # Repeated errors to trigger incident
ERROR_WINDOW_HOURS = 1      # Time window for error counting
DEPENDENCY_ERROR_THRESHOLD = 3


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

        dependency_incidents = await self._detect_dependency_unreachable(db)
        detected.extend(dependency_incidents)
        
        return detected
    
    async def _detect_restart_loops(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect containers with excessive restarts using raw status facts."""
        since = datetime.utcnow() - timedelta(hours=1)
        
        # Get recent container_status facts
        result = await db.execute(
            select(Fact)
            .where(Fact.fact_type == "container_status")
            .where(Fact.timestamp >= since)
            .order_by(Fact.timestamp.desc())
        )
        facts = list(result.scalars().all())
        
        # Group by resource_ref to find the latest state
        latest_status = {}
        for fact in facts:
            if fact.resource_ref not in latest_status:
                latest_status[fact.resource_ref] = fact
        
        incidents = []
        for resource_ref, fact in latest_status.items():
            restart_count = fact.value.get("restart_count", 0)
            
            if restart_count >= RESTART_LOOP_THRESHOLD:
                # Check if incident already exists
                existing = await self._get_open_incident(db, resource_ref)
                if existing:
                    continue
                
                container_name = fact.value.get("name", "unknown")
                
                # Create incident
                incident = await self._create_incident(
                    db,
                    severity=IncidentSeverity.high if restart_count > 5 else IncidentSeverity.medium,
                    affected_resources=[resource_ref],
                    symptoms=[
                        f"Container {container_name} has high restart count: {restart_count}",
                        f"Status: {fact.value.get('status')}",
                        f"Detected at: {fact.timestamp.isoformat()}",
                    ],
                    summary=f"Restart loop detected: {container_name}",
                )
                
                incidents.append({
                    "incident_id": incident.id,
                    "type": "restart_loop",
                    "resource": resource_ref,
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

        file_sources = await db.execute(
            select(FileLogSource).where(FileLogSource.enabled.is_(True))
        )
        for source in file_sources.scalars().all():
            resource_ref = source.resource_ref
            existing = await self._get_open_incident(db, resource_ref)
            if existing:
                continue

            errors = await log_collector.extract_error_signatures(
                db, resource_ref, hours=ERROR_WINDOW_HOURS
            )
            if len(errors) >= ERROR_REPEAT_THRESHOLD:
                keywords = set(e["keyword"] for e in errors)
                incident = await self._create_incident(
                    db,
                    severity=IncidentSeverity.medium,
                    affected_resources=[resource_ref],
                    symptoms=[
                        f"File log source {source.name} has {len(errors)} errors in the last hour",
                        f"Error types: {', '.join(keywords)}",
                        f"Sample: {errors[0]['content'][:100]}...",
                    ],
                    summary=f"Repeated file log errors in {source.name}",
                )
                incidents.append({
                    "incident_id": incident.id,
                    "type": "file_error_pattern",
                    "resource": resource_ref,
                    "error_count": len(errors),
                    "keywords": list(keywords),
                })
        
        return incidents

    async def _detect_dependency_unreachable(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Detect dependency unreachable issues from logs."""
        dependency_keywords = [
            "connection refused",
            "connection timed out",
            "timeout",
            "unreachable",
            "no route to host",
            "name or service not known",
            "temporary failure in name resolution",
        ]

        result = await db.execute(
            select(Fact)
            .where(Fact.fact_type == "container_status")
            .where(Fact.timestamp >= datetime.utcnow() - timedelta(hours=1))
        )
        container_facts = list(result.scalars().all())

        incidents = []
        resources = {fact.resource_ref for fact in container_facts}

        file_sources = await db.execute(
            select(FileLogSource).where(FileLogSource.enabled.is_(True))
        )
        resources.update(source.resource_ref for source in file_sources.scalars().all())

        for resource_ref in resources:
            existing = await self._get_open_incident(db, resource_ref)
            if existing:
                continue

            logs = await log_collector.get_logs(db, resource_ref, limit=200, since_hours=ERROR_WINDOW_HOURS)
            matches = []
            for log in logs:
                content_lower = log.content.lower()
                for keyword in dependency_keywords:
                    if keyword in content_lower:
                        matches.append((keyword, log))
                        break

            if len(matches) >= DEPENDENCY_ERROR_THRESHOLD:
                keywords = sorted({keyword for keyword, _ in matches})
                incident = await self._create_incident(
                    db,
                    severity=IncidentSeverity.medium,
                    affected_resources=[resource_ref],
                    symptoms=[
                        f"Dependency unreachable errors detected ({len(matches)} occurrences)",
                        f"Error types: {', '.join(keywords)}",
                        f"Sample: {matches[0][1].content[:100]}...",
                    ],
                    summary="Dependency unreachable detected",
                )
                incidents.append({
                    "incident_id": incident.id,
                    "type": "dependency_unreachable",
                    "resource": resource_ref,
                    "error_count": len(matches),
                    "keywords": keywords,
                })

        return incidents
    
    async def _get_open_incident(
        self, 
        db: AsyncSession, 
        resource_ref: str
    ) -> Incident | None:
        """Check if there's already an open incident for this resource."""
        # Fetch all open/investigating incidents first
        result = await db.execute(
            select(Incident)
            .where(Incident.status.in_([IncidentStatus.open, IncidentStatus.investigating]))
        )
        incidents = result.scalars().all()
        
        # Filter in Python because 'json' type doesn't support containment operators well
        for incident in incidents:
            if resource_ref in incident.affected_resources:
                return incident
        return None
    
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
        asyncio.create_task(notification_router.notify_incident(incident))
        
        return incident


# Singleton
incident_detector = IncidentDetector()
