"""Summary Generator - generates log summaries for long-term storage."""

from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import LogEntry
from homelab.rag.rag_indexer import rag_indexer


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
        
        summary = self._summarize_logs_locally(resource_ref, logs)
        
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
        
        return (
            f"## Monthly Log Summary for {resource_ref} ({year}-{month:02d})\n\n"
            f"- Days summarized: {len(summaries)}\n\n"
            "### Daily Highlights\n"
            f"{combined}\n"
        )

    def _summarize_logs_locally(self, resource_ref: str, logs: list[LogEntry]) -> str:
        """Generate a deterministic summary without LLM calls."""
        total_logs = len(logs)
        sources = Counter(log.log_source for log in logs)
        keywords = ["error", "exception", "failed", "fatal", "panic", "crash"]
        keyword_counts = Counter()
        samples = []

        for log in logs:
            content = log.content.strip()
            if len(samples) < 5 and content:
                samples.append(f"- [{log.timestamp.isoformat()}] {content[:200]}")
            lower = content.lower()
            for keyword in keywords:
                if keyword in lower:
                    keyword_counts[keyword] += 1
                    break

        source_summary = ", ".join(f"{name}: {count}" for name, count in sources.items())
        keyword_summary = (
            ", ".join(f"{key}: {count}" for key, count in keyword_counts.most_common())
            if keyword_counts
            else "none detected"
        )
        samples_text = "\n".join(samples) if samples else "- (no sample lines captured)"

        return (
            f"## Log Summary for {resource_ref}\n\n"
            f"- Total entries: {total_logs}\n"
            f"- Sources: {source_summary}\n"
            f"- Error keywords: {keyword_summary}\n\n"
            "### Sample Entries\n"
            f"{samples_text}\n"
        )


# Singleton
summary_generator = SummaryGenerator()
