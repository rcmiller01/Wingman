"""Narrative Generator - Uses LLM to summarize incidents."""

import json
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.config import get_settings
from homelab.storage.models import Incident, IncidentNarrative, Fact, LogEntry

settings = get_settings()

class NarrativeGenerator:
    """Generates human-readable narratives for incidents using local LLM."""
    
    def __init__(self):
        self.ollama_url = settings.ollama_host  # e.g. "http://host.docker.internal:11434"
        self.model = settings.ollama_model      # e.g. "llama3" or "mistral"
        
    async def generate_narrative(self, db: AsyncSession, incident_id: str) -> IncidentNarrative | None:
        """Generate a narrative for a specific incident."""
        
        # 1. Fetch Incident and related data
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if not incident:
            return None
            
        # 2. Fetch related Facts (symptoms)
        # In a real system, we'd fetch specific facts linked to symptoms.
        # For MVP, we'll fetch recent facts for the affected resources.
        facts = []
        for resource_ref in incident.affected_resources:
            fact_result = await db.execute(
                select(Fact)
                .where(Fact.resource_ref == resource_ref)
                .order_by(Fact.timestamp.desc())
                .limit(5)
            )
            facts.extend(fact_result.scalars().all())

        # 3. Fetch recent Logs for context
        logs = []
        for resource_ref in incident.affected_resources:
            log_result = await db.execute(
                select(LogEntry)
                .where(LogEntry.resource_ref == resource_ref)
                .order_by(LogEntry.timestamp.desc())
                .limit(20)
            )
            logs.extend(log_result.scalars().all())
            
        # 4. Construct Prompt
        prompt = self._construct_prompt(incident, facts, logs)
        
        # 5. Call LLM
        narrative_text = await self._call_ollama(prompt)
        
        # 6. Create/Update IncidentNarrative
        # Check if narrative already exists
        narrative_result = await db.execute(select(IncidentNarrative).where(IncidentNarrative.incident_id == incident_id))
        narrative = narrative_result.scalar_one_or_none()
        
        if narrative:
            narrative.narrative_text = narrative_text
            narrative.updated_at = datetime.utcnow()
        else:
            narrative = IncidentNarrative(
                incident_id=incident_id,
                time_range={"start": incident.detected_at.isoformat(), "end": None},
                narrative_text=narrative_text,
                evidence_refs=[f"fact:{f.id}" for f in facts] + [f"log:{l.id}" for l in logs],
                resolution_steps=[],
            )
            db.add(narrative)
            
        return narrative

    def _construct_prompt(self, incident: Incident, facts: list[Fact], logs: list[LogEntry]) -> str:
        """Construct the prompt for the LLM."""
        
        fact_str = "\n".join([f"- [{f.timestamp}] {f.fact_type}: {f.value}" for f in facts])
        log_str = "\n".join([f"- [{l.timestamp}] {l.log_source}: {l.content[:200]}" for l in logs])
        symptom_str = "\n".join([f"- {s}" for s in incident.symptoms])
        
        return f"""
You are an expert Site Reliability Engineer (SRE). Analyze the following incident and write a concise, technical narrative.

**Incident Details:**
- Severity: {incident.severity.value}
- Affected Resources: {', '.join(incident.affected_resources)}
- Detected At: {incident.detected_at}

**Symptoms:**
{symptom_str}

**Recent Infrastructure Facts:**
{fact_str}

**Recent Logs:**
{log_str}

**Instructions:**
1. Summarize what is happening.
2. Identify potential root causes based on the logs and facts.
3. Suggest 2-3 specific troubleshooting steps.
4. Format output in Markdown.

**Narrative:**
"""

    async def _call_ollama(self, prompt: str) -> str:
        """Call the Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "Error: Empty response from LLM")
        except Exception as e:
            print(f"[NarrativeGenerator] LLM Error: {e}")
            return f"**Error generating narrative:** {str(e)}"

# Singleton
narrative_generator = NarrativeGenerator()
