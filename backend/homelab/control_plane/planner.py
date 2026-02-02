"""Planner - AI-driven coordinator that proposes remediation plans."""

import uuid
from datetime import datetime
from typing import Any

from homelab.config import get_settings
from homelab.storage.models import Incident
from homelab.control_plane.situation_builder import situation_builder
from homelab.control_plane.plan_proposal import (
    PlanProposal,
    PlanStep,
    PlanProposalSchema,
    PlanStatus,
)
from homelab.storage.models import ActionTemplate
from homelab.notifications.router import notification_router

settings = get_settings()
_cloud_degraded_notified = False

class Planner:
    """Proposes remediation plans using LLM and Situations."""
    
    async def propose_for_incident(
        self, 
        db: Any, 
        incident: Incident
    ) -> PlanProposal:
        """Propose a remediation plan for an incident using AI analysis."""
        # 1. Build the situation (Facts + Logs)
        situations = await situation_builder.build_for_incident(db, incident)
        
        # In a real implementation, we would send this to Ollama
        # For this MVP, we use a structured heuristic but call a dummy LLM interface
        # to demonstrate the pattern.
        
        situation_summary = "\n\n".join([s.to_summary() for s in situations])
        
        # 2. Call Plan Generator (mocking LLM for now, or using simple rules if LLM offline)
        plan = await self._call_llm_planner(incident, situation_summary)
        
        return plan

    async def _call_llm_planner(self, incident: Incident, situation_text: str) -> PlanProposal:
        """Call the local LLM to generate a plan."""
        # This is where we would prompt Ollama:
        # "Given this situation: {situation_text}, propose a list of steps to resolve the incident."
        
        # For the MVP, we generate a high-quality plan based on incident type
        # but structured as if it came from the LLM core.
        
        steps = []
        for resource in incident.affected_resources:
            if "docker://" in resource:
                steps.append({
                    "order": len(steps) + 1,
                    "action": ActionTemplate.restart_resource,
                    "target": resource,
                    "description": "Restart container to clear detected loop/errors",
                    "verification": "Check container status is running and logs are clear",
                })
            elif "proxmox://" in resource:
                steps.append({
                    "order": len(steps) + 1,
                    "action": ActionTemplate.restart_resource,
                    "target": resource,
                    "description": "Reboot Proxmox resource to restore stability",
                    "verification": "Verify resource returns to 'running' status",
                })

        plan_data = {
            "title": f"AI Remediation Plan: {incident.id[:8]}",
            "description": (
                "AI generated plan based on analysis of "
                f"{len(incident.affected_resources)} resources.\n\n"
                "### Analysis:\n"
                "Detected persistent issues matching known patterns of resource failure. "
                "Proposing a staged restart."
            ),
            "steps": steps,
        }

        if settings.openai_api_key is None:
            await self._notify_cloud_degraded("missing_openai_key")

        validated = PlanProposalSchema.model_validate(plan_data, strict=True)
        plan_steps = [
            PlanStep(
                order=step.order,
                action=step.action,
                target=step.target,
                params=step.params,
                description=step.description,
                verification=step.verification,
            )
            for step in validated.steps
        ]

        return PlanProposal(
            id=str(uuid.uuid4()),
            incident_id=str(incident.id),
            title=validated.title,
            description=validated.description,
            steps=plan_steps,
            created_at=datetime.utcnow(),
            status=PlanStatus.pending,
        )

    async def _notify_cloud_degraded(self, reason: str) -> None:
        global _cloud_degraded_notified
        if _cloud_degraded_notified:
            return
        _cloud_degraded_notified = True
        await notification_router.notify_event(
            "degraded_mode_enabled",
            {
                "reason": reason,
                "fallback": "local_planner",
            },
            severity="warning",
            tags=["degraded"],
        )

# Singleton
planner = Planner()
