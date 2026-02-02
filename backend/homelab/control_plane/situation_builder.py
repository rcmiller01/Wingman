"""Situation Builder - aggregates facts and logs into a 'Situation' for the Planner."""

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.models import Fact, LogEntry
from homelab.storage.models import Incident

class Situation:
    """A collection of relevant facts and logs for analysis."""
    def __init__(self, resource_ref: str, facts: list[Fact], logs: list[LogEntry]):
        self.resource_ref = resource_ref
        self.facts = facts
        self.logs = logs
        self.timestamp = datetime.utcnow()

    def to_summary(self) -> str:
        """Format the situation for LLM consumption."""
        summary = f"Situation Report for {self.resource_ref}\n"
        summary += "=" * 40 + "\n"
        
        summary += "\nRecent Facts:\n"
        for fact in self.facts:
            summary += f"- [{fact.timestamp.isoformat()}] {fact.fact_type}: {fact.value}\n"
            
        summary += "\nRecent LogEntrys:\n"
        for log in self.logs:
            summary += f"- [{log.timestamp.isoformat()}] {log.log_source}: {log.content[:200]}\n"
            
        return summary

class SituationBuilder:
    """Builds situations from the storage layer."""
    
    async def build_for_resource(
        self, 
        db: AsyncSession, 
        resource_ref: str, 
        hours: int = 1
    ) -> Situation:
        """Build a situation for a specific resource."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get facts
        fact_result = await db.execute(
            select(Fact)
            .where(Fact.resource_ref == resource_ref)
            .where(Fact.timestamp >= since)
            .order_by(Fact.timestamp.desc())
        )
        facts = list(fact_result.scalars().all())
        
        # Get logs
        log_result = await db.execute(
            select(LogEntry)
            .where(LogEntry.resource_ref == resource_ref)
            .where(LogEntry.timestamp >= since)
            .order_by(LogEntry.timestamp.desc())
            .limit(100)
        )
        logs = list(log_result.scalars().all())
        
        return Situation(resource_ref, facts, logs)

    async def build_for_incident(
        self, 
        db: AsyncSession, 
        incident: Incident
    ) -> list[Situation]:
        """Build situations for all resources affected by an incident."""
        situations = []
        for resource_ref in incident.affected_resources:
            situation = await self.build_for_resource(db, resource_ref)
            situations.append(situation)
        return situations

# Singleton
situation_builder = SituationBuilder()
