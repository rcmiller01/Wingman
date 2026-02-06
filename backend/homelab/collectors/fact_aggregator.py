"""Cross-site fact aggregation and deduplication."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import Fact


async def aggregate_facts_by_site(
    db: AsyncSession,
    *,
    fact_type: str,
    time_window: timedelta = timedelta(hours=1),
) -> dict[str, list[dict[str, Any]]]:
    """Aggregate facts by site within a time window.
    
    Args:
        db: Database session
        fact_type: Type of facts to aggregate (e.g., 'docker_container', 'proxmox_vm')
        time_window: Time window to consider (default: 1 hour)
    
    Returns:
        Dictionary mapping site names to lists of facts
    """
    cutoff = datetime.now(timezone.utc) - time_window
    
    query = (
        select(Fact)
        .where(
            Fact.fact_type == fact_type,
            Fact.timestamp >= cutoff,
        )
        .order_by(Fact.site_name, Fact.timestamp.desc())
    )
    
    result = await db.execute(query)
    facts = result.scalars().all()
    
    # Group by site
    by_site: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        if fact.site_name not in by_site:
            by_site[fact.site_name] = []
        by_site[fact.site_name].append({
            "id": fact.id,
            "source": fact.source,
            "worker_id": fact.worker_id,
            "data": fact.data,
            "timestamp": fact.timestamp.isoformat(),
        })
    
    return by_site


async def get_cross_site_summary(
    db: AsyncSession,
    *,
    fact_type: str,
    time_window: timedelta = timedelta(hours=1),
) -> dict[str, Any]:
    """Get cross-site summary statistics for a fact type.
    
    Args:
        db: Database session
        fact_type: Type of facts to summarize
        time_window: Time window to consider
    
    Returns:
        Summary statistics including total count, count by site, etc.
    """
    by_site = await aggregate_facts_by_site(db, fact_type=fact_type, time_window=time_window)
    
    total_count = sum(len(facts) for facts in by_site.values())
    site_counts = {site: len(facts) for site, facts in by_site.items()}
    
    return {
        "fact_type": fact_type,
        "time_window_hours": time_window.total_seconds() / 3600,
        "total_count": total_count,
        "site_count": len(by_site),
        "by_site": site_counts,
        "sites": list(by_site.keys()),
    }


async def deduplicate_fact(
    db: AsyncSession,
    *,
    fact_type: str,
    source: str,
    data: dict[str, Any],
    site_name: str,
    worker_id: str | None = None,
) -> Fact | None:
    """Insert fact with deduplication.
    
    If a fact with the same dedup_key already exists, returns None.
    Otherwise, inserts the fact and returns it.
    
    Args:
        db: Database session
        fact_type: Type of fact
        source: Source of the fact
        data: Fact data
        site_name: Site where fact was collected
        worker_id: Worker that collected the fact
    
    Returns:
        The inserted Fact, or None if it already exists
    """
    # Generate dedup key from fact_type + source + key data fields
    # For example: "docker_container:docker://host1:container-id-123"
    resource_id = data.get("id", data.get("name", ""))
    dedup_key = f"{fact_type}:{source}:{resource_id}"
    
    # Check if fact already exists
    existing = await db.execute(
        select(Fact).where(Fact.dedup_key == dedup_key)
    )
    if existing.scalar_one_or_none():
        return None  # Already exists
    
    # Insert new fact
    fact = Fact(
        fact_type=fact_type,
        source=source,
        site_name=site_name,
        worker_id=worker_id,
        data=data,
        dedup_key=dedup_key,
    )
    db.add(fact)
    await db.flush()
    return fact


async def merge_facts_across_sites(
    db: AsyncSession,
    *,
    fact_type: str,
    merge_strategy: str = "latest",
    time_window: timedelta = timedelta(hours=1),
) -> list[dict[str, Any]]:
    """Merge facts across sites using a merge strategy.
    
    Args:
        db: Database session
        fact_type: Type of facts to merge
        merge_strategy: How to merge duplicates ("latest", "all", "deduplicate")
        time_window: Time window to consider
    
    Returns:
        List of merged facts
    """
    by_site = await aggregate_facts_by_site(db, fact_type=fact_type, time_window=time_window)
    
    if merge_strategy == "all":
        # Return all facts from all sites
        merged = []
        for site_facts in by_site.values():
            merged.extend(site_facts)
        return merged
    
    elif merge_strategy == "latest":
        # For each unique resource, keep only the latest fact
        resource_map: dict[str, dict[str, Any]] = {}
        
        for site_facts in by_site.values():
            for fact in site_facts:
                resource_id = fact["data"].get("id", fact["data"].get("name", ""))
                if not resource_id:
                    continue
                
                # Keep the latest fact for this resource
                if resource_id not in resource_map:
                    resource_map[resource_id] = fact
                else:
                    existing_ts = datetime.fromisoformat(resource_map[resource_id]["timestamp"])
                    new_ts = datetime.fromisoformat(fact["timestamp"])
                    if new_ts > existing_ts:
                        resource_map[resource_id] = fact
        
        return list(resource_map.values())
    
    elif merge_strategy == "deduplicate":
        # Remove exact duplicates based on dedup_key
        seen_keys = set()
        merged = []
        
        for site_facts in by_site.values():
            for fact in site_facts:
                resource_id = fact["data"].get("id", fact["data"].get("name", ""))
                dedup_key = f"{fact_type}:{fact['source']}:{resource_id}"
                
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    merged.append(fact)
        
        return merged
    
    else:
        raise ValueError(f"Unknown merge strategy: {merge_strategy}")
