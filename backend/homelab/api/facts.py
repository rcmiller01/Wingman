"""Facts API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
from typing import Any

from homelab.storage import get_db
from homelab.collectors import fact_collector

router = APIRouter(prefix="/api/facts", tags=["facts"])


class FactEntry(BaseModel):
    """Fact entry response model."""
    id: str
    resource_ref: str
    fact_type: str
    value: dict[str, Any]
    timestamp: datetime
    source: str
    
    class Config:
        from_attributes = True


@router.get("")
async def get_facts(
    resource_ref: str | None = None,
    fact_type: str | None = None,
    hours: int = Query(24, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get recent facts, optionally filtered."""
    facts = await fact_collector.get_recent_facts(
        db,
        resource_ref=resource_ref,
        fact_type=fact_type,
        hours=hours,
    )
    
    return {
        "count": len(facts),
        "facts": [FactEntry.model_validate(f) for f in facts],
    }


@router.post("/collect")
async def collect_facts(db: AsyncSession = Depends(get_db)):
    """Trigger fact collection from all adapters."""
    counts = await fact_collector.collect_all(db)
    await db.commit()
    
    return {
        "collected": counts,
        "total": sum(counts.values()),
    }
