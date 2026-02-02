"""Plan Generator - Proposes actions based on incidents."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import (
    Incident,
    IncidentStatus,
    ActionHistory,
    ActionTemplate,
    ActionStatus,
)

class PlanGenerator:
    """Generates remediation plans using heuristics (MVP) or LLM (Future)."""
    
    async def generate_plans(self, db: AsyncSession, incident_id: str) -> list[ActionHistory]:
        """Generate proposed actions for an incident."""
        
        # 1. Fetch Incident
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if not incident:
            return []
            
        # 2. Check for existing plans to avoid duplicates
        existing_plans = await db.execute(
            select(ActionHistory)
            .where(ActionHistory.incident_id == incident_id)
            .where(ActionHistory.status.in_([ActionStatus.pending, ActionStatus.approved, ActionStatus.executing]))
        )
        if existing_plans.scalars().first():
            return []

        proposed_actions = []
        
        # 3. Heuristic Planning (MVP)
        # In a real system, this would be a sophisticated policy engine or LLM
        
        # Rule 1: Restart Loops -> Propose Restart
        # Check if any symptom mentions "high restart count"
        restart_symptom = any("restart count" in s for s in incident.symptoms)
        
        if restart_symptom:
            for resource_ref in incident.affected_resources:
                if resource_ref.startswith("docker://"):
                    proposed_actions.append(
                        ActionHistory(
                            incident_id=incident.id,
                            action_template=ActionTemplate.restart_resource,
                            target_resource=resource_ref,
                            parameters={"timeout": 30},
                            status=ActionStatus.pending
                        )
                    )
        
        # Rule 2: Stopped Resource -> Propose Start
        # (This is just an example, might trigger for 'Status: exited')
        if "Status: exited" in str(incident.symptoms):
             for resource_ref in incident.affected_resources:
                if resource_ref.startswith("docker://"):
                    proposed_actions.append(
                        ActionHistory(
                            incident_id=incident.id,
                            action_template=ActionTemplate.start_resource,
                            target_resource=resource_ref,
                            parameters={},
                            status=ActionStatus.pending
                        )
                    )

        # 4. Save Proposals
        for action in proposed_actions:
            db.add(action)
            print(f"[PlanGenerator] Proposed action {action.action_template} for {action.target_resource}")
            
        return proposed_actions

# Singleton
plan_generator = PlanGenerator()
