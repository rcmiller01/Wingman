"""Audit chain utilities for tamper-resistant logging.

Provides hash chain functionality for ActionHistory to ensure immutability
and enable tamper detection. Each entry includes:
- prev_hash: SHA256 of the previous entry
- entry_hash: SHA256 of (prev_hash + action_template + target + timestamp)
- sequence_num: Monotonic counter for ordering

This creates a blockchain-like structure where tampering with any entry
breaks the chain for all subsequent entries.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import ActionHistory

logger = logging.getLogger(__name__)

# Genesis hash for the first entry in the chain
GENESIS_HASH = "0" * 64  # 64 zeros (SHA256 produces 64 hex chars)


def compute_entry_hash(
    prev_hash: str,
    action_template: str,
    target_resource: str,
    requested_at: datetime,
    result: dict | None = None,
) -> str:
    """
    Compute SHA256 hash for an audit entry.
    
    The hash covers the key immutable fields of the entry:
    - Previous entry hash (chain link)
    - Action template
    - Target resource
    - Request timestamp
    - Result summary (if present)
    
    Returns lowercase hex string (64 chars).
    """
    content = f"{prev_hash}|{action_template}|{target_resource}|{requested_at.isoformat()}"
    
    # Include result hash if present (but not full content to keep hash stable)
    if result:
        result_hash = hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()[:16]
        content += f"|{result_hash}"
    
    return hashlib.sha256(content.encode()).hexdigest()


async def get_chain_head(db: AsyncSession) -> tuple[str, int]:
    """
    Get the hash and sequence number of the last entry in the chain.
    
    Returns (prev_hash, next_sequence_num) for creating a new entry.
    If chain is empty, returns (GENESIS_HASH, 1).
    """
    query = select(ActionHistory.entry_hash, ActionHistory.sequence_num).order_by(
        desc(ActionHistory.sequence_num)
    ).limit(1)
    
    result = await db.execute(query)
    row = result.first()
    
    if row and row.entry_hash and row.sequence_num:
        return row.entry_hash, row.sequence_num + 1
    
    return GENESIS_HASH, 1


async def prepare_chained_entry(
    db: AsyncSession,
    action: ActionHistory,
) -> ActionHistory:
    """
    Prepare an ActionHistory entry with hash chain fields.
    
    Call this before adding the entry to the session.
    Sets prev_hash, entry_hash, and sequence_num.
    """
    prev_hash, seq_num = await get_chain_head(db)
    
    action.prev_hash = prev_hash
    action.sequence_num = seq_num
    action.entry_hash = compute_entry_hash(
        prev_hash=prev_hash,
        action_template=action.action_template.value,
        target_resource=action.target_resource,
        requested_at=action.requested_at,
        result=action.result,
    )
    
    return action


async def verify_chain_integrity(
    db: AsyncSession,
    start_seq: int = 1,
    end_seq: int | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Verify the integrity of the audit chain.
    
    Recomputes hashes for each entry and verifies:
    1. Each entry's hash matches its content
    2. Each entry's prev_hash matches the previous entry's entry_hash
    3. Sequence numbers are contiguous
    
    Returns (is_valid, list_of_violations).
    
    Violations include:
    - {"type": "hash_mismatch", "sequence_num": N, "expected": "...", "actual": "..."}
    - {"type": "chain_break", "sequence_num": N, "expected_prev": "...", "actual_prev": "..."}
    - {"type": "sequence_gap", "expected": N, "actual": M}
    """
    violations = []
    
    # Build query
    query = select(ActionHistory).order_by(ActionHistory.sequence_num)
    if end_seq:
        query = query.where(ActionHistory.sequence_num <= end_seq)
    query = query.where(ActionHistory.sequence_num >= start_seq)
    
    result = await db.execute(query)
    entries = list(result.scalars().all())
    
    if not entries:
        return True, []
    
    expected_prev_hash = GENESIS_HASH if start_seq == 1 else None
    expected_seq = start_seq
    
    for entry in entries:
        # Skip entries without hash chain (legacy data)
        if entry.entry_hash is None or entry.sequence_num is None:
            continue
        
        # Check sequence continuity
        if entry.sequence_num != expected_seq:
            violations.append({
                "type": "sequence_gap",
                "expected": expected_seq,
                "actual": entry.sequence_num,
                "entry_id": entry.id,
            })
        
        # Check chain link
        if expected_prev_hash is not None and entry.prev_hash != expected_prev_hash:
            violations.append({
                "type": "chain_break",
                "sequence_num": entry.sequence_num,
                "expected_prev": expected_prev_hash,
                "actual_prev": entry.prev_hash,
                "entry_id": entry.id,
            })
        
        # Recompute hash and verify
        computed_hash = compute_entry_hash(
            prev_hash=entry.prev_hash or GENESIS_HASH,
            action_template=entry.action_template.value,
            target_resource=entry.target_resource,
            requested_at=entry.requested_at,
            result=entry.result,
        )
        
        if entry.entry_hash != computed_hash:
            violations.append({
                "type": "hash_mismatch",
                "sequence_num": entry.sequence_num,
                "expected": computed_hash,
                "actual": entry.entry_hash,
                "entry_id": entry.id,
            })
        
        # Update expectations for next iteration
        expected_prev_hash = entry.entry_hash
        expected_seq = entry.sequence_num + 1
    
    return len(violations) == 0, violations


async def get_chain_summary(db: AsyncSession) -> dict[str, Any]:
    """
    Get a summary of the audit chain for monitoring.
    
    Returns:
    - total_entries: Number of entries with hash chain
    - latest_sequence: Highest sequence number
    - latest_hash: Hash of the most recent entry
    - chain_valid: Quick integrity check result
    """
    # Count entries with hash chain
    count_query = select(func.count()).select_from(ActionHistory).where(
        ActionHistory.entry_hash.isnot(None)
    )
    count_result = await db.execute(count_query)
    total_entries = count_result.scalar() or 0
    
    # Get latest entry
    latest_query = select(
        ActionHistory.sequence_num,
        ActionHistory.entry_hash,
        ActionHistory.requested_at,
    ).where(
        ActionHistory.entry_hash.isnot(None)
    ).order_by(desc(ActionHistory.sequence_num)).limit(1)
    
    latest_result = await db.execute(latest_query)
    latest = latest_result.first()
    
    # Quick integrity check (just verify latest entry)
    chain_valid = True
    if latest and total_entries > 0:
        is_valid, _ = await verify_chain_integrity(
            db, 
            start_seq=max(1, (latest.sequence_num or 1) - 5),  # Check last 5
            end_seq=latest.sequence_num
        )
        chain_valid = is_valid
    
    return {
        "total_entries": total_entries,
        "latest_sequence": latest.sequence_num if latest else None,
        "latest_hash": latest.entry_hash if latest else None,
        "latest_timestamp": latest.requested_at.isoformat() if latest else None,
        "chain_valid": chain_valid,
    }
