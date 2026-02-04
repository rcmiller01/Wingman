#!/usr/bin/env python3
"""
Generate test ActionHistory entries for audit chain verification.

This script creates a series of test entries with proper hash chain
linking to validate the audit chain infrastructure.

Usage:
  export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/wingman"
  python scripts/generate_test_audit_entries.py [count]

Arguments:
  count   Number of entries to generate (default: 10)
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
import random

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus
from homelab.storage.audit_chain import prepare_chained_entry


# Test scenarios for realistic audit entries
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
        "action_template": ActionTemplate.collect_diagnostics,
        "target_resource": "docker://wingman-test-nginx",
        "parameters": {"lines": 50, "include_stderr": True},
        "status": ActionStatus.completed,
        "result": {"logs_collected": 48, "errors_found": 0},
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
    {
        "action_template": ActionTemplate.verify_resource_health,
        "target_resource": "docker://wingman-qdrant-1",
        "parameters": {"check_type": "http", "path": "/health"},
        "status": ActionStatus.completed,
        "result": {"healthy": True, "status_code": 200},
    },
    {
        "action_template": ActionTemplate.validate_network_connectivity,
        "target_resource": "docker://wingman-test-nginx",
        "parameters": {"target": "8.8.8.8", "port": 53},
        "status": ActionStatus.completed,
        "result": {"reachable": True, "latency_ms": 15},
    },
    {
        "action_template": ActionTemplate.collect_diagnostics,
        "target_resource": "docker://wingman-postgres-1",
        "parameters": {"lines": 200, "since": "24h"},
        "status": ActionStatus.completed,
        "result": {"logs_collected": 892, "size_bytes": 145920},
    },
]


async def generate_entries(db_url: str, count: int) -> int:
    """Generate test audit entries with proper hash chain."""
    
    print(f"🔧 Generating {count} test audit entries...")
    print()
    
    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    base_time = datetime.utcnow() - timedelta(hours=count)
    created = 0
    
    for i in range(count):
        # Create new session for each entry to ensure proper chain linking
        async with SessionLocal() as session:
            # Pick a random scenario
            scenario = random.choice(TEST_SCENARIOS)
            
            # Create the action with timestamps offset by minutes
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
                # Actor attribution
                requested_by_user_id="test-user",
                requested_by_role="admin",
                requested_by_key_id="test1234...",
                approved_by_user_id="test-user",
                approved_by_role="admin",
                executed_by_user_id="system",
                executed_by_role="executor",
            )
            
            # Prepare with hash chain (this sets prev_hash, entry_hash, sequence_num)
            await prepare_chained_entry(session, action)
            
            session.add(action)
            await session.commit()
            
            print(f"  ✓ Entry {i+1}/{count}: seq={action.sequence_num}, "
                  f"hash={action.entry_hash[:12]}..., "
                  f"action={action.action_template.value}")
            
            created += 1
    
    await engine.dispose()
    
    print()
    print(f"✅ Created {created} entries with hash chain")
    
    return created


def main() -> int:
    """Main entry point."""
    # Get count from args
    count = 10
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"Invalid count: {sys.argv[1]}")
            return 1
    
    # Get database URL
    db_url = os.getenv("DATABASE_URL") or os.getenv("WINGMAN_DATABASE_URL")
    
    if not db_url:
        print("ERROR: DATABASE_URL or WINGMAN_DATABASE_URL is not set.")
        return 1
    
    if "asyncpg" not in db_url:
        print("ERROR: Database URL must use asyncpg driver.")
        return 1
    
    # Generate entries
    asyncio.run(generate_entries(db_url, count))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
