
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

# Minimal imports
from homelab.storage.database import async_session_maker
from homelab.storage.models import ActionTemplate, ActionHistory, ActionStatus, TodoStep
from homelab.control_plane.plan_proposal import PlanProposal, PlanStep
from homelab.policy.policy_engine import policy_engine
from datetime import datetime


from unittest.mock import MagicMock, AsyncMock


from unittest.mock import MagicMock, AsyncMock

async def run_checks():
    print("--- Starting Isolated Policy Checks (Mocked DB) ---")
    
    # Mock DB
    db = MagicMock()
    # Explicitly make execute async
    db.execute = AsyncMock()
    
    # Check 1: Denylist
    print("Checking Denylist...")
    proposal = PlanProposal(
        id="test1",
        incident_id="test",
        title="t", description="d", created_at=datetime.utcnow(), steps=[
            PlanStep(
                order=1,
                action=ActionTemplate.stop_resource,
                target="docker://storage-controller"
            )
        ]
    )
    is_valid, violations = await policy_engine.validate(db, proposal)
    if not is_valid and any("DENYLIST" in v for v in violations):
        print("PASS: Denylist checked.")
    else:
        print(f"FAIL: Denylist check failed. Valid: {is_valid}, Violations: {violations}")

    # Check 2: Rate Limit
    print("Checking Rate Limit...")
    
    # Mock db.execute return value for Rate Limit check
    
    mock_result = MagicMock()
    mock_result.scalar.return_value = 3
    # Configure the AsyncMock to return the mock_result
    db.execute.return_value = mock_result
    
    proposal2 = PlanProposal(
        id="test2",
        incident_id="test",
        title="t", description="d", created_at=datetime.utcnow(), steps=[
            PlanStep(
                order=1,
                action=ActionTemplate.restart_resource,
                target="docker://spam-container"
            )
        ]
    )
    is_valid, violations = await policy_engine.validate(db, proposal2)
    
    if not is_valid and any("Rate limit exceeded" in v for v in violations):
        print("PASS: Rate Limit checked.")
    else:
        print(f"FAIL: Rate Limit check failed. Valid: {is_valid}, Violations: {violations}")

if __name__ == "__main__":
    asyncio.run(run_checks())
