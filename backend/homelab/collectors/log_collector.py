"""LogEntry Collector - ingests logs with retention metadata."""

from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from homelab.storage.models import LogEntry, FileLogSource, Fact
from homelab.adapters import docker_adapter


# LogEntry retention: 90 days
LOG_RETENTION_DAYS = 90


class LogEntryCollector:
    """Collects and stores container logs with retention tracking."""
    
    async def collect_container_logs(
        self,
        db: AsyncSession,
        container_id: str,
        since_minutes: int = 60,
    ) -> int:
        """Collect logs from a specific container."""
        if not docker_adapter.is_connected:
            return 0
        
        container = await docker_adapter.get_container(container_id)
        if not container:
            return 0
        
        logs = await docker_adapter.get_logs(
            container_id, 
            since_minutes=since_minutes,
            tail=1000,
        )
        
        count = 0
        retention_date = datetime.utcnow() + timedelta(days=LOG_RETENTION_DAYS)
        
        for entry in logs:
            log = LogEntry(
                resource_ref=container["resource_ref"],
                log_source=entry["source"],
                content=entry["content"],
                timestamp=entry["timestamp"],
                retention_date=retention_date,
            )
            db.add(log)
            count += 1
        
        return count
    
    async def collect_all_container_logs(
        self,
        db: AsyncSession,
        since_minutes: int = 60,
    ) -> dict[str, int]:
        """Collect logs from all running containers."""
        if not docker_adapter.is_connected:
            return {}
        
        containers = await docker_adapter.list_containers(all=False)  # Only running
        results = {}
        
        for container in containers:
            count = await self.collect_container_logs(
                db,
                container["id"],
                since_minutes=since_minutes,
            )
            results[container["name"]] = count
        
        return results

    async def collect_file_logs(self, db: AsyncSession, source: FileLogSource, max_lines: int = 500) -> int:
        """Tail an opt-in file log source and store new entries."""
        if not source.enabled:
            return 0

        path = Path(source.path)
        if not path.exists() or not path.is_file():
            return 0

        retention_date = datetime.utcnow() + timedelta(days=source.retention_days)
        count = 0

        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            handle.seek(source.last_position)
            for _ in range(max_lines):
                line = handle.readline()
                if not line:
                    break
                content = line.rstrip("\n")
                if not content:
                    continue
                log = LogEntry(
                    resource_ref=source.resource_ref,
                    log_source="file",
                    content=content,
                    timestamp=datetime.utcnow(),
                    retention_date=retention_date,
                )
                db.add(log)
                count += 1

            source.last_position = handle.tell()

        return count

    async def collect_all_file_logs(self, db: AsyncSession) -> dict[str, int]:
        """Collect logs from all enabled file log sources."""
        result = await db.execute(select(FileLogSource).where(FileLogSource.enabled.is_(True)))
        sources = result.scalars().all()

        results: dict[str, int] = {}
        for source in sources:
            count = await self.collect_file_logs(db, source)
            results[source.name] = count

        return results
    
    async def get_logs(
        self,
        db: AsyncSession,
        resource_ref: str,
        limit: int = 100,
        since_hours: int | None = None,
    ) -> list[LogEntry]:
        """Get logs for a resource."""
        query = select(LogEntry).where(LogEntry.resource_ref == resource_ref)
        
        if since_hours:
            since = datetime.utcnow() - timedelta(hours=since_hours)
            query = query.where(LogEntry.timestamp >= since)
        
        query = query.order_by(LogEntry.timestamp.desc()).limit(limit)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def purge_expired_logs(self, db: AsyncSession) -> int:
        """Delete logs past their retention date."""
        now = datetime.utcnow()
        from homelab.rag.log_summarizer import log_summarizer
        await log_summarizer.summarize_expiring_logs(db, retention_days=LOG_RETENTION_DAYS)
        
        result = await db.execute(
            delete(LogEntry).where(LogEntry.retention_date < now)
        )
        
        return result.rowcount or 0
    
    async def extract_error_signatures(
        self,
        db: AsyncSession,
        resource_ref: str,
        hours: int = 24,
    ) -> list[dict]:
        """Extract error patterns from recent logs (for incident detection)."""
        logs = await self.get_logs(db, resource_ref, limit=500, since_hours=hours)
        
        error_patterns = []
        error_keywords = ["error", "exception", "failed", "fatal", "panic", "crash"]

        since = datetime.utcnow() - timedelta(hours=hours)
        existing_facts = await db.execute(
            select(Fact)
            .where(Fact.resource_ref == resource_ref)
            .where(Fact.fact_type == "log_error_signature")
            .where(Fact.timestamp >= since)
        )
        known_log_ids = {
            fact.value.get("log_id")
            for fact in existing_facts.scalars().all()
            if isinstance(fact.value, dict)
        }
        
        for log in logs:
            content_lower = log.content.lower()
            for keyword in error_keywords:
                if keyword in content_lower:
                    error_patterns.append({
                        "log_id": log.id,
                        "timestamp": log.timestamp.isoformat(),
                        "content": log.content[:200],  # Truncate for safety
                        "keyword": keyword,
                        "source": log.log_source,
                    })
                    if log.id not in known_log_ids:
                        db.add(
                            Fact(
                                resource_ref=resource_ref,
                                fact_type="log_error_signature",
                                value={
                                    "log_id": log.id,
                                    "keyword": keyword,
                                    "source": log.log_source,
                                    "content": log.content[:200],
                                },
                                source="logs",
                                timestamp=log.timestamp,
                            )
                        )
                    break  # Only match first keyword per log
        
        return error_patterns


# Singleton
log_collector = LogEntryCollector()
