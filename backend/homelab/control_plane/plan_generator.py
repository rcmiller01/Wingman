"""Plan Generator - creates remediation plans from incidents."""

import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import Incident
from homelab.control_plane.plan_proposal import (
    PlanProposal, 
    PlanStep, 
    ActionType, 
    PlanStatus,
)


class PlanGenerator:
    """Generates remediation plans from incidents."""
    
    async def generate_for_incident(
        self,
        db: AsyncSession,
        incident: Incident,
    ) -> PlanProposal:
        """Generate a remediation plan for an incident."""
        steps = []
        
        # Analyze symptoms to determine actions
        for resource in incident.affected_resources:
            if resource.startswith("docker://"):
                # For Docker containers, suggest restart
                steps.append(PlanStep(
                    order=len(steps) + 1,
                    action=ActionType.restart_container,
                    target=resource,
                    description=f"Restart container to clear error state",
                    verification="Verify container status is 'running' and no new errors in logs",
                ))
        
        # Create plan
        plan = PlanProposal(
            id=str(uuid.uuid4()),
            incident_id=str(incident.id),
            title=f"Remediation plan for incident {str(incident.id)[:8]}",
            description=self._generate_description(incident),
            steps=steps,
            created_at=datetime.utcnow(),
            status=PlanStatus.pending,
        )
        
        return plan
    
    def _generate_description(self, incident: Incident) -> str:
        """Generate a plan description from incident symptoms."""
        symptoms = "\n".join(f"- {s}" for s in incident.symptoms)
        return f"""Automated remediation plan for detected incident.

**Severity:** {incident.severity.value}

**Symptoms:**
{symptoms}

This plan will attempt to restore normal operation by restarting affected services.
"""

    def create_manual_plan(
        self,
        title: str,
        description: str,
        steps: list[dict],
        incident_id: str | None = None,
    ) -> PlanProposal:
        """Create a plan from manual specification."""
        plan_steps = []
        for i, step_data in enumerate(steps):
            plan_steps.append(PlanStep(
                order=i + 1,
                action=ActionType(step_data["action"]),
                target=step_data["target"],
                params=step_data.get("params", {}),
                description=step_data.get("description", ""),
                verification=step_data.get("verification"),
            ))
        
        return PlanProposal(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            title=title,
            description=description,
            steps=plan_steps,
            created_at=datetime.utcnow(),
            status=PlanStatus.pending,
        )


# Singleton
plan_generator = PlanGenerator()
