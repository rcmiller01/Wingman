"""Narrative Generator - generates incident narratives using local LLM."""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.config import get_settings
from homelab.storage.models import Incident, IncidentNarrative
from homelab.llm.validators import NarrativeOutput
from homelab.collectors import log_collector


settings = get_settings()

# Timeout for LLM calls
LLM_TIMEOUT_SECONDS = 120


class NarrativeGenerator:
    """Generates incident narratives using local Ollama LLM."""
    
    async def generate_narrative(
        self,
        db: AsyncSession,
        incident: Incident,
    ) -> str:
        """Generate a narrative for an incident using local LLM."""
        # Gather context
        context = await self._build_context(db, incident)
        
        # Build prompt
        prompt = self._build_prompt(incident, context)
        
        # Call local LLM
        try:
            narrative = await self._call_ollama(prompt)
            return NarrativeOutput.model_validate({"text": narrative}, strict=True).text
        except Exception as e:
            print(f"[NarrativeGenerator] LLM call failed: {e}")
            return self._fallback_narrative(incident, context)
    
    async def _build_context(
        self, 
        db: AsyncSession, 
        incident: Incident
    ) -> dict:
        """Build context from logs and facts."""
        context = {
            "error_logs": [],
            "symptoms": incident.symptoms,
        }
        
        # Get error logs for affected resources
        for resource_ref in incident.affected_resources:
            errors = await log_collector.extract_error_signatures(
                db, resource_ref, hours=24
            )
            context["error_logs"].extend(errors[:10])  # Limit to 10 per resource
        
        return context
    
    def _build_prompt(self, incident: Incident, context: dict) -> str:
        """Build the LLM prompt."""
        symptoms_text = "\n".join(f"- {s}" for s in incident.symptoms)
        
        error_text = ""
        if context["error_logs"]:
            error_text = "\n\nRecent Error Logs:\n"
            for err in context["error_logs"][:5]:  # Limit for prompt size
                error_text += f"- [{err['timestamp']}] {err['content'][:150]}\n"
        
        prompt = f"""You are a DevOps incident analyst. Analyze this infrastructure incident and provide a concise narrative.

**Incident Details:**
- Severity: {incident.severity.value}
- Affected Resources: {', '.join(incident.affected_resources)}
- Detected: {incident.detected_at.isoformat()}

**Symptoms:**
{symptoms_text}
{error_text}

**Instructions:**
1. Summarize what happened
2. Suggest a likely root cause hypothesis
3. Recommend immediate actions (as bullet points)
4. Keep the response under 300 words

Generate the incident narrative:"""
        
        return prompt
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama for generation."""
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    
    def _fallback_narrative(self, incident: Incident, context: dict) -> str:
        """Generate a simple narrative without LLM."""
        symptoms_text = "\n".join(f"- {s}" for s in incident.symptoms)
        
        narrative = f"""## Incident Report

**Severity:** {incident.severity.value.upper()}

**Affected Resources:**
{', '.join(incident.affected_resources)}

**Symptoms Observed:**
{symptoms_text}

**Analysis:**
The system detected anomalous behavior in the affected resources. Manual investigation recommended.

**Recommended Actions:**
- Review container logs for additional error details
- Check resource utilization (CPU, memory)
- Verify dependent services are healthy
- Consider restarting the affected container if symptoms persist

*Note: Automated LLM analysis unavailable. This is a fallback narrative.*
"""
        return narrative
    
    async def update_incident_narrative(
        self,
        db: AsyncSession,
        incident_id: str,
        narrative_text: str,
        root_cause: str | None = None,
        confidence: float | None = None,
    ):
        """Update an incident's narrative."""
        from sqlalchemy import select
        
        result = await db.execute(
            select(IncidentNarrative).where(IncidentNarrative.incident_id == incident_id)
        )
        narrative = result.scalars().first()
        
        if narrative:
            narrative.narrative_text = narrative_text
            if root_cause:
                narrative.root_cause_hypothesis = root_cause
            if confidence:
                narrative.confidence = confidence


# Singleton
narrative_generator = NarrativeGenerator()
