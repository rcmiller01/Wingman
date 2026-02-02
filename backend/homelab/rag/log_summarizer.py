"""Log Summarizer - Compresses historical logs into RAG-able summaries."""

import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from homelab.storage.models import LogEntry, LogSummary
from homelab.rag.narrative_generator import narrative_generator
from homelab.rag.vector_store import vector_store

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
                .limit(100)
            )
            logs_res = await db.execute(log_query)
            logs = logs_res.scalars().all()
            
            if not logs:
                continue
                
            log_text = "\n".join([f"[{l.timestamp}] {l.level}: {l.message}" for l in logs])
            
            # 2. Generate Summary via Ollama
            prompt = f"""
            SYSTEM: You are a system administrator. Summarize the following log lines for {resource_ref}. 
            Identify key patterns, error spikes, and root causes if visible.
            Keep summary concise (under 200 words).
            
            LOGS:
            {log_text}
            """
            
            summary_text = await narrative_generator.query_llm(prompt)
            
            # 3. Store Summary
            start_date = logs[0].timestamp
            end_date = logs[-1].timestamp
            
            summary = LogSummary(
                resource_ref=resource_ref,
                summary_text=summary_text,
                start_date=start_date,
                end_date=end_date,
                log_count=count
            )
            db.add(summary)
            await db.commit()
            await db.refresh(summary)
            
            # 4. Index in Vector Store
            await vector_store.index_log_summary(
                summary_id=str(summary.id),
                text=summary_text,
                meta={
                    "resource": resource_ref,
                    "start": str(start_date),
                    "end": str(end_date)
                }
            )
            
            summarized_count += count
            
        return summarized_count

# Singleton
log_summarizer = LogSummarizer()
