"""Log Summarizer - Compresses historical logs into RAG-able summaries."""

from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from homelab.storage.models import LogEntry, LogSummary
from homelab.rag.rag_indexer import rag_indexer
from homelab.notifications.router import notification_router

class LogSummarizer:
    """Summarizes logs before they are purged."""
    
    async def summarize_expiring_logs(self, db: AsyncSession, retention_days: int = 90) -> int:
        """Find logs near expiry, summarize them, and store summaries."""
        # Target logs expiring in the next 24 hours (or already expired but not purged)
        cutoff = datetime.utcnow() - timedelta(days=retention_days - 1)
        
        # 1. Group by Resource
        # We want to know which resources have expiring logs
        query = (
            select(LogEntry.resource_ref, func.count(LogEntry.id))
            .where(LogEntry.timestamp < cutoff)
            .group_by(LogEntry.resource_ref)
        )
        result = await db.execute(query)
        groups = result.all()
        
        summarized_count = 0
        
        for resource_ref, count in groups:
            print(f"[LogSummarizer] Consolidating {count} logs for {resource_ref}...")
            
            # Fetch sample of logs (first 50 and last 50 error logs ideally)
            # For MVP, just grab up to 100 logs
            log_query = (
                select(LogEntry)
                .where(LogEntry.resource_ref == resource_ref)
                .where(LogEntry.timestamp < cutoff)
                .order_by(LogEntry.timestamp.asc())
                .limit(100)
            )
            logs_res = await db.execute(log_query)
            logs = logs_res.scalars().all()
            
            if not logs:
                continue
                
            summary_text = self._summarize_logs_locally(resource_ref, logs)
            
            # 3. Store Summary
            start_date = logs[0].timestamp
            end_date = logs[-1].timestamp
            retention_date = datetime.utcnow() + timedelta(days=365)
            
            summary = LogSummary(
                resource_ref=resource_ref,
                summary_text=summary_text,
                period_start=start_date,
                period_end=end_date,
                log_count=count,
                retention_date=retention_date,
            )
            db.add(summary)
            await db.commit()
            await db.refresh(summary)
            
            # 4. Index in Vector Store
            await rag_indexer.index_log_summary(
                resource_ref=resource_ref,
                summary_text=summary_text,
                time_range={
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                metadata={
                    "summary_id": str(summary.id),
                    "log_count": count,
                },
            )

            await notification_router.notify_event(
                "digest_ready",
                {
                    "summary_id": str(summary.id),
                    "resource_ref": resource_ref,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "log_count": count,
                },
                severity="info",
                tags=["digest"],
            )
            
            summarized_count += count
            
        return summarized_count

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
log_summarizer = LogSummarizer()
