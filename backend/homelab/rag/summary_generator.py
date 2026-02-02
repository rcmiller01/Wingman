"""Summary Generator - generates log summaries for long-term storage."""

import httpx
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.config import get_settings
from homelab.storage.models import LogEntry
from homelab.rag.rag_indexer import rag_indexer
from homelab.llm.validators import SummaryOutput


settings = get_settings()

# Summary generation timeout
LLM_TIMEOUT_SECONDS = 120


class SummaryGenerator:
    """Generates compressed log summaries for long-term retention."""
    
    async def generate_daily_summary(
        self,
        db: AsyncSession,
        resource_ref: str,
        date: datetime,
    ) -> str | None:
        """Generate a summary of logs for a specific day."""
        # Get logs for the day
        start = datetime(date.year, date.month, date.day)
        end = start + timedelta(days=1)
        
        result = await db.execute(
            select(LogEntry)
            .where(LogEntry.resource_ref == resource_ref)
            .where(LogEntry.timestamp >= start)
            .where(LogEntry.timestamp < end)
            .order_by(LogEntry.timestamp)
            .limit(500)
        )
        logs = list(result.scalars().all())
        
        if not logs:
            return None
        
        # Build log text
        log_text = "\n".join([
            f"[{log.timestamp.strftime('%H:%M:%S')}] [{log.log_source}] {log.content[:200]}"
            for log in logs
        ])
        
        # Truncate if too long
        if len(log_text) > 8000:
            log_text = log_text[:8000] + "\n... (truncated)"
        
        # Generate summary
        prompt = f"""Summarize the following container logs from {date.strftime('%Y-%m-%d')}.
Focus on:
1. Key events and state changes
2. Any errors or warnings
3. Performance patterns
4. Notable anomalies

LogEntrys:
{log_text}

Provide a concise Markdown summary (under 500 words):"""
        
        summary = await self._call_llm(prompt)
        if summary:
            summary = SummaryOutput.model_validate({"text": summary}, strict=True).text
        
        if summary:
            # Index into RAG
            await rag_indexer.index_log_summary(
                resource_ref=resource_ref,
                summary_text=summary,
                time_range={
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
                metadata={
                    "log_count": len(logs),
                    "date": date.strftime("%Y-%m-%d"),
                },
            )
        
        return summary
    
    async def generate_monthly_rollup(
        self,
        db: AsyncSession,
        resource_ref: str,
        year: int,
        month: int,
    ) -> str | None:
        """Generate a monthly rollup summary from daily summaries."""
        # Search for daily summaries in the time range
        query = f"logs summary {resource_ref} {year}-{month:02d}"
        summaries = await rag_indexer.search_summaries(query, limit=31)
        
        if not summaries:
            return None
        
        # Combine summaries
        combined = "\n\n---\n\n".join([
            f"**{s.get('time_range', {}).get('start', 'Unknown date')}**\n{s['text']}"
            for s in summaries
        ])
        
        if len(combined) > 6000:
            combined = combined[:6000] + "\n... (truncated)"
        
        prompt = f"""Create a monthly executive summary from these daily log summaries for {year}-{month:02d}.
Highlight:
1. Major incidents and resolutions
2. Recurring patterns or issues
3. Overall system health trends
4. Key metrics if available

Daily Summaries:
{combined}

Provide a concise monthly summary (under 300 words):"""
        
        summary = await self._call_llm(prompt)
        if summary:
            return SummaryOutput.model_validate({"text": summary}, strict=True).text
        return summary
    
    async def _call_llm(self, prompt: str) -> str | None:
        """Call Ollama for generation."""
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response")
                
        except Exception as e:
            print(f"[SummaryGenerator] LLM error: {e}")
            return None


# Singleton
summary_generator = SummaryGenerator()
