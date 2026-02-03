"""Narrative Generator - Uses LLM to summarize incidents."""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import Incident, IncidentNarrative, Fact, LogEntry
from homelab.llm.validators import NarrativeOutput
from homelab.llm.providers import llm_manager, LLMFunction

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generates human-readable narratives for incidents using configured LLM."""

    def __init__(self):
        pass  # Uses llm_manager singleton for LLM operations
        
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
            
        # 4. RAG: Search for similar past incidents and historical log patterns
        from homelab.rag.rag_indexer import rag_indexer

        search_query = f"Incident on {', '.join(incident.affected_resources)}: {', '.join(incident.symptoms)}"
        similar_docs = await rag_indexer.search_narratives(search_query, limit=2)
        log_summaries = await rag_indexer.search_summaries(search_query, limit=2)

        # 5. Construct Prompt
        prompt = self._construct_prompt(incident, facts, logs, similar_docs, log_summaries)
        
        # 6. Call LLM
        narrative_text = await self._call_llm(prompt)
        narrative_text = NarrativeOutput.model_validate({"text": narrative_text}, strict=True).text
        
        # 7. Create/Update IncidentNarrative
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
            await db.commit()
            await db.refresh(narrative) # Re-fetch to guarantee ID for indexing

        # 8. Index Narrative
        await rag_indexer.index_narrative(
            narrative_id=str(narrative.id),
            narrative_text=narrative_text,
            incident_id=str(incident.id),
            metadata={
                "severity": incident.severity.value,
                "symptoms": incident.symptoms,
            },
        )
            
        return narrative

    def _construct_prompt(self, incident: Incident, facts: list[Fact], logs: list[LogEntry], similar_docs: list = None, log_summaries: list = None) -> str:
        """Construct the prompt for the LLM."""

        fact_str = "\n".join([f"- [{f.timestamp}] {f.fact_type}: {f.value}" for f in facts])
        log_str = "\n".join([f"- [{l.timestamp}] {l.log_source}: {l.content[:200]}" for l in logs])
        symptom_str = "\n".join([f"- {s}" for s in incident.symptoms])

        rag_context = ""
        if similar_docs:
            rag_context = "**Similar Past Incidents:**\n"
            for doc in similar_docs:
                rag_context += f"- [Score {doc['score']:.2f}] {doc.get('text', '')[:200]}...\n"
            rag_context += "\n"

        history_context = ""
        if log_summaries:
            history_context = "**Historical Log Patterns:**\n"
            for summary in log_summaries:
                history_context += f"- [Score {summary['score']:.2f}] {summary.get('text', '')[:300]}...\n"
            history_context += "\n"

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

{rag_context}{history_context}**Instructions:**
1. Summarize what is happening.
2. Identify potential root causes based on the logs and facts.
3. Suggest 2-3 specific troubleshooting steps.
4. If similar incidents are provided, check if the current issue follows a pattern.
5. If historical log patterns are provided, note any recurring issues or trends.
6. Format output in Markdown.

**Narrative:**
"""

    async def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider."""
        try:
            return await llm_manager.generate(prompt, function=LLMFunction.CHAT)
        except Exception as e:
            logger.error("[NarrativeGenerator] LLM Error: %s", e)
            return f"**Error generating narrative:** {str(e)}"

# Singleton
narrative_generator = NarrativeGenerator()
