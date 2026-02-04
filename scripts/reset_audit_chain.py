#!/usr/bin/env python3
"""
Reset and rebuild the audit chain from scratch.

This script:
1. Deletes all existing ActionHistory entries
2. Creates a clean set of test entries with proper sequential chaining

USE WITH CAUTION - this deletes audit data!

Usage:
  export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/wingman"
  python scripts/reset_audit_chain.py [count]
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus
from homelab.storage.audit_chain import prepare_chained_entry, GENESIS_HASH


# Test scenarios
TEST_SCENARIOS = [
    {
        "action_template": ActionTemplate.verify_resource_health,
        "target_resource": "docker://wingman-test-nginx",
        "parameters": {"check_type": "http", "timeout": 5},
        "status": ActionStatus.completed,
        "result": {"healthy": True, "response_time_ms": 42},
    },
    {
        "action_template": ActionTemplate.collect_diagnostics,
        "target_resource": "docker://wingman-test-redis",
        "parameters": {"lines": 100, "since": "1h"},
        "status": ActionStatus.completed,
        "result": {"logs_collected": 156, "size_bytes": 24576},
    },
    {
        "action_template": ActionTemplate.verify_resource_health,
        "target_resource": "docker://wingman-postgres-1",
        "parameters": {"check_type": "tcp", "port": 5432},
        "status": ActionStatus.completed,
        "result": {"healthy": True, "connection_established": True},
    },
    {
        "action_template": ActionTemplate.restart_resource,
        "target_resource": "docker://wingman-test-alpine",
        "parameters": {"graceful": True, "timeout": 30},
        "status": ActionStatus.completed,
        "result": {"restarted": True, "downtime_seconds": 2.5},
    },
    {
        "action_template": ActionTemplate.stop_resource,
        "target_resource": "docker://wingman-test-alpine",
        "parameters": {"graceful": True},
        "status": ActionStatus.completed,
        "result": {"stopped": True, "exit_code": 0},
    },
    {
        "action_template": ActionTemplate.start_resource,
        "target_resource": "docker://wingman-test-alpine",
        "parameters": {},
        "status": ActionStatus.completed,
        "result": {"started": True, "container_id": "abc123def456"},
    },
]


async def reset_and_rebuild(db_url: str, count: int) -> int:
    """Reset audit chain and create clean test entries."""
    
    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Step 1: Delete all existing entries
    print("🗑️  Deleting existing ActionHistory entries...")
    async with SessionLocal() as session:
        result = await session.execute(delete(ActionHistory))
        deleted = result.rowcount
        await session.commit()
    print(f"   Deleted {deleted} entries")
    print()
    
    # Step 2: Create new entries with proper chain
    print(f"🔧 Creating {count} new entries with proper hash chain...")
    base_time = datetime.utcnow() - timedelta(hours=count)
    
    prev_hash = GENESIS_HASH
    for i in range(count):
        async with SessionLocal() as session:
            scenario = random.choice(TEST_SCENARIOS)
            
            action = ActionHistory(
                action_template=scenario["action_template"],
                target_resource=scenario["target_resource"],
                parameters=scenario["parameters"],
                status=scenario["status"],
                result=scenario["result"],
                requested_at=base_time + timedelta(minutes=i * 5),
                approved_at=base_time + timedelta(minutes=i * 5, seconds=1),
                executed_at=base_time + timedelta(minutes=i * 5, seconds=2),
                completed_at=base_time + timedelta(minutes=i * 5, seconds=5),
                requested_by_user_id="test-user",
                requested_by_role="admin",
                requested_by_key_id="test1234",
                approved_by_user_id="test-user",
                approved_by_role="admin",
                executed_by_user_id="system",
                executed_by_role="executor",
            )
            
            # Use prepare_chained_entry to properly set hash chain
            await prepare_chained_entry(session, action)
            
            session.add(action)
            await session.commit()
            
            # Refresh to get final values
            await session.refresh(action)
            
            print(f"   ✓ seq={action.sequence_num:2d} | hash={action.entry_hash[:12]}... | "
                  f"prev={action.prev_hash[:12]}... | {action.action_template.value}")
            
            prev_hash = action.entry_hash
    
    await engine.dispose()
    
    print()
    print(f"✅ Created {count} properly chained entries")
    return count


def main() -> int:
    count = 15
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"Invalid count: {sys.argv[1]}")
            return 1
    
    db_url = os.getenv("DATABASE_URL") or os.getenv("WINGMAN_DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1
    
    if "asyncpg" not in db_url:
        print("ERROR: Must use asyncpg driver")
        return 1
    
    # Confirm destructive action
    print("⚠️  WARNING: This will DELETE all ActionHistory entries!")
    print()
    
    asyncio.run(reset_and_rebuild(db_url, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
