#!/usr/bin/env python3
"""
Verify Wingman ActionHistory audit hash chain integrity.

Usage:
  # Set database URL (must use asyncpg driver)
  export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/wingman"
  python scripts/verify_audit_chain.py

  # Or use the WINGMAN_ prefix
  export WINGMAN_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/wingman"
  python scripts/verify_audit_chain.py

Exit codes:
  0 = Chain is valid
  1 = Configuration error
  2 = Chain verification failed (tampering or corruption detected)
  3 = No entries found (nothing to verify)
"""

import os
import sys
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from homelab.storage.models import ActionHistory
from homelab.storage.audit_chain import (
    verify_chain_integrity,
    get_chain_summary,
    GENESIS_HASH,
)


def print_banner(text: str, char: str = "=") -> None:
    """Print a banner with text centered."""
    width = 60
    print(char * width)
    print(text.center(width))
    print(char * width)


async def run_verification(db_url: str) -> int:
    """
    Run full audit chain verification against the database.
    
    Returns exit code.
    """
    print_banner("Wingman Audit Chain Verification")
    print()
    
    # Create engine and session
    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # 1. Get chain summary first
        print("📊 Chain Summary")
        print("-" * 40)
        
        summary = await get_chain_summary(session)
        
        total = summary.get("total_entries", 0)
        latest_seq = summary.get("latest_sequence")
        latest_hash = summary.get("latest_hash")
        latest_ts = summary.get("latest_timestamp")
        
        print(f"  Total entries with hash chain: {total}")
        print(f"  Latest sequence number: {latest_seq}")
        print(f"  Latest entry hash: {latest_hash[:16]}..." if latest_hash else "  Latest entry hash: None")
        print(f"  Latest timestamp: {latest_ts}")
        print()
        
        if total == 0:
            print("⚠️  No ActionHistory entries with hash chain found.")
            print("   Nothing to verify. Generate some actions first.")
            await engine.dispose()
            return 3
        
        # 2. Check for gaps in sequence numbers
        print("🔢 Sequence Analysis")
        print("-" * 40)
        
        # Get min/max sequence and count
        stats_query = select(
            func.min(ActionHistory.sequence_num).label("min_seq"),
            func.max(ActionHistory.sequence_num).label("max_seq"),
            func.count().label("count"),
        ).where(ActionHistory.sequence_num.isnot(None))
        
        stats_result = await session.execute(stats_query)
        stats = stats_result.first()
        
        min_seq = stats.min_seq
        max_seq = stats.max_seq
        count = stats.count
        expected = (max_seq - min_seq + 1) if min_seq and max_seq else 0
        
        print(f"  Sequence range: {min_seq} to {max_seq}")
        print(f"  Actual count: {count}")
        print(f"  Expected (contiguous): {expected}")
        
        if count != expected:
            print(f"  ⚠️  Gap detected: {expected - count} missing sequence numbers")
        else:
            print(f"  ✅ No sequence gaps detected")
        print()
        
        # 3. Check for missing hashes
        print("🔐 Hash Coverage")
        print("-" * 40)
        
        hash_query = select(
            func.count().filter(ActionHistory.entry_hash.is_(None)).label("missing_entry_hash"),
            func.count().filter(ActionHistory.prev_hash.is_(None)).label("missing_prev_hash"),
            func.count().label("total"),
        )
        
        hash_result = await session.execute(hash_query)
        hash_stats = hash_result.first()
        
        missing_entry = hash_stats.missing_entry_hash
        missing_prev = hash_stats.missing_prev_hash
        total_entries = hash_stats.total
        
        print(f"  Total ActionHistory entries: {total_entries}")
        print(f"  Entries missing entry_hash: {missing_entry}")
        print(f"  Entries missing prev_hash: {missing_prev}")
        
        if missing_entry > 0 or missing_prev > 0:
            print(f"  ⚠️  Some entries missing hash chain data (legacy?)")
        else:
            print(f"  ✅ All entries have hash chain data")
        print()
        
        # 4. Verify genesis entry
        print("🌱 Genesis Entry Check")
        print("-" * 40)
        
        genesis_query = select(ActionHistory).where(
            ActionHistory.sequence_num == 1
        ).limit(1)
        
        genesis_result = await session.execute(genesis_query)
        genesis = genesis_result.scalar_one_or_none()
        
        if genesis:
            print(f"  Genesis entry ID: {genesis.id[:8]}...")
            print(f"  Genesis prev_hash: {genesis.prev_hash[:16] if genesis.prev_hash else 'None'}...")
            if genesis.prev_hash == GENESIS_HASH:
                print(f"  ✅ Genesis prev_hash is correct (all zeros)")
            else:
                print(f"  ⚠️  Genesis prev_hash unexpected (expected {GENESIS_HASH[:16]}...)")
        else:
            print("  ⚠️  No genesis entry (sequence_num=1) found")
        print()
        
        # 5. Full chain verification
        print("🔗 Full Chain Verification")
        print("-" * 40)
        
        is_valid, violations = await verify_chain_integrity(session)
        
        if is_valid:
            print(f"  ✅ Audit chain is VALID")
            print(f"  Verified {total} entries from seq {min_seq} to {max_seq}")
        else:
            print(f"  ❌ Audit chain FAILED verification")
            print(f"  Found {len(violations)} violation(s):")
            print()
            
            for i, v in enumerate(violations[:10], 1):  # Show first 10
                vtype = v.get("type", "unknown")
                if vtype == "hash_mismatch":
                    print(f"    {i}. HASH MISMATCH at sequence {v.get('sequence_num')}")
                    print(f"       Expected: {v.get('expected', 'N/A')[:32]}...")
                    print(f"       Actual:   {v.get('actual', 'N/A')[:32]}...")
                elif vtype == "chain_break":
                    print(f"    {i}. CHAIN BREAK at sequence {v.get('sequence_num')}")
                    print(f"       Expected prev: {v.get('expected_prev', 'N/A')[:32]}...")
                    print(f"       Actual prev:   {v.get('actual_prev', 'N/A')[:32]}...")
                elif vtype == "sequence_gap":
                    print(f"    {i}. SEQUENCE GAP")
                    print(f"       Expected: {v.get('expected')}")
                    print(f"       Actual:   {v.get('actual')}")
                else:
                    print(f"    {i}. {vtype}: {v}")
                print()
            
            if len(violations) > 10:
                print(f"    ... and {len(violations) - 10} more violations")
        
        print()
        
    await engine.dispose()
    
    # Return appropriate exit code
    if is_valid:
        print_banner("✅ AUDIT CHAIN VERIFIED", "=")
        return 0
    else:
        print_banner("❌ AUDIT CHAIN COMPROMISED", "!")
        return 2


def main() -> int:
    """Main entry point."""
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL") or os.getenv("WINGMAN_DATABASE_URL")
    
    if not db_url:
        print("ERROR: DATABASE_URL or WINGMAN_DATABASE_URL is not set.")
        print()
        print("Set one of these environment variables to your PostgreSQL URL:")
        print("  export DATABASE_URL='postgresql+asyncpg://user:pass@host:5432/wingman'")
        print()
        return 1
    
    # Ensure asyncpg driver is used
    if "asyncpg" not in db_url:
        print("ERROR: Database URL must use asyncpg driver.")
        print()
        print("Current URL starts with:", db_url[:40] + "...")
        print()
        print("Change 'postgresql://' to 'postgresql+asyncpg://'")
        print()
        return 1
    
    # Run verification
    return asyncio.run(run_verification(db_url))


if __name__ == "__main__":
    sys.exit(main())
