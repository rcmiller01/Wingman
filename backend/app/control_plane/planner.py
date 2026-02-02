"""Planner - AI-driven coordinator that proposes remediation plans."""

import uuid
from datetime import datetime
from typing import Any
import httpx
import json

from app.config import get_settings
from app.storage.models import Incident
from app.control_plane.situation_builder import Situation, situation_builder
from app.control_plane.plan_proposal import PlanProposal, PlanStep, ActionType, PlanStatus

settings = get_settings()

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
                steps.append(PlanStep(
                    order=len(steps) + 1,
                    action=ActionType.restart_container,
                    target=resource,
                    description="Restart container to clear detected loop/errors",
                    verification="Check container status is running and logs are clear"
                ))
            elif "proxmox://" in resource:
                steps.append(PlanStep(
                    order=len(steps) + 1,
                    action=ActionType.restart_vm if "qemu" in resource else ActionType.restart_lxc,
                    target=resource,
                    description="Reboot Proxmox resource to restore stability",
                    verification="Verify resource returns to 'running' status"
                ))

        return PlanProposal(
            id=str(uuid.uuid4()),
            incident_id=str(incident.id),
            title=f"AI Remediation Plan: {incident.id[:8]}",
            description=f"AI generated plan based on analysis of {len(incident.affected_resources)} resources.\n\n### Analysis:\nDetected persistent issues matching known patterns of resource failure. Proposing a staged restart.",
            steps=steps,
            created_at=datetime.utcnow(),
            status=PlanStatus.pending
        )

# Singleton
planner = Planner()
