"""End-to-end happy path integration test.

Tests the complete incident remediation flow:
1. Create incident
2. Propose plan
3. Validate plan
4. Create todos
5. (Mock) Execute step
6. Record ActionHistory + incident narrative
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import (
    Incident,
    IncidentStatus,
    IncidentSeverity,
    TodoStep,
    ActionStatus,
    ActionTemplate,
    ActionHistory,
    IncidentNarrative,
)
from homelab.control_plane.plan_proposal import PlanProposal, PlanStep, PlanStatus
from homelab.policy.policy_engine import policy_engine


@pytest.fixture
async def clean_db(async_db):
    """Clean up test data before and after tests using the async_db fixture."""
    db = async_db
    # Cleanup before test
    await db.execute(delete(TodoStep))
    await db.execute(delete(ActionHistory))
    await db.execute(delete(IncidentNarrative))
    await db.execute(delete(Incident))
    await db.commit()
    
    yield db
    
    # Cleanup after test
    await db.execute(delete(TodoStep))
    await db.execute(delete(ActionHistory))
    await db.execute(delete(IncidentNarrative))
    await db.execute(delete(Incident))
    await db.commit()


@pytest.mark.asyncio
async def test_complete_incident_remediation_happy_path(clean_db):
    """
    Test the complete incident remediation flow end-to-end.
    
    Flow: INCIDENT -> PLAN -> VALIDATE -> TODO -> APPROVAL -> EXECUTE -> VERIFY -> RECORD
    """
    db = clean_db
    # =========================================
    # STEP 1: Create Incident
    # =========================================
    incident = Incident(
        severity=IncidentSeverity.high,
        status=IncidentStatus.open,
        affected_resources=["docker://test-container"],
        symptoms=["High Memory Usage", "Container OOM killed"],
        detected_at=datetime.utcnow()
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    
    incident_id = incident.id
    assert incident_id is not None
    assert incident.status == IncidentStatus.open
    
    # =========================================
    # STEP 2: Create Plan Proposal
    # =========================================
    proposal = PlanProposal(
        id=f"plan-{incident_id[:8]}",
        incident_id=incident_id,
        title="Restart High Memory Container",
        description="Restarting container to reclaim memory after OOM event",
        created_at=datetime.utcnow(),
        steps=[
            PlanStep(
                order=1,
                action=ActionTemplate.restart_resource,
                target="docker://test-container",
                description="Restart the container to reclaim memory",
                verification="Check container is running and memory usage < 80%"
            )
        ]
    )
    
    assert proposal.status == PlanStatus.pending
    assert len(proposal.steps) == 1
    
    # =========================================
    # STEP 3: Validate Plan (Policy Engine)
    # =========================================
    is_valid, violations = await policy_engine.validate(db, proposal)
    
    # Should pass - restart_resource is allowed, target not on denylist
    assert is_valid, f"Policy rejected valid plan: {violations}"
    assert len(violations) == 0
    
    # =========================================
    # STEP 4: Create TodoStep (Queue for approval)
    # =========================================
    todo = TodoStep(
        plan_id=proposal.id,
        incident_id=incident_id,
        order=1,
        action_template=ActionTemplate.restart_resource,
        target_resource="docker://test-container",
        parameters={},
        status=ActionStatus.pending
    )
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    
    assert todo.id is not None
    assert todo.status == ActionStatus.pending
    
    # =========================================
    # STEP 5: Approve TodoStep
    # =========================================
    todo.status = ActionStatus.approved
    todo.approved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(todo)
    
    assert todo.status == ActionStatus.approved
    assert todo.approved_at is not None
    
    # =========================================
    # STEP 6: Execute (Mocked Docker Adapter)
    # =========================================
    from homelab.control_plane.executor_router import executor_router
    
    # Mock the docker adapter restart
    with patch('homelab.control_plane.executor_router.docker_adapter') as mock_docker:
        mock_docker.restart_container = AsyncMock(return_value=True)
        
        # Update todo to executing
        todo.status = ActionStatus.executing
        await db.commit()
        
        # Execute via router
        result = await executor_router.execute_step(proposal.steps[0])
        
        assert result["success"] is True
        assert result["adapter"] == "docker"
        mock_docker.restart_container.assert_called_once_with("test-container")
    
    # =========================================
    # STEP 7: Record ActionHistory (Audit Trail)
    # =========================================
    action_record = ActionHistory(
        incident_id=incident_id,
        action_template=ActionTemplate.restart_resource,
        target_resource="docker://test-container",
        parameters={},
        status=ActionStatus.completed,
        requested_at=todo.approved_at,
        approved_at=todo.approved_at,
        executed_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        result={"success": True, "adapter": "docker"}
    )
    db.add(action_record)
    await db.commit()
    await db.refresh(action_record)
    
    assert action_record.id is not None
    assert action_record.status == ActionStatus.completed
    assert action_record.result is not None
    
    # =========================================
    # STEP 8: Update Todo and Incident Status
    # =========================================
    todo.status = ActionStatus.completed
    await db.commit()
    
    # Mark incident as mitigated (verification would confirm resolution)
    incident.status = IncidentStatus.mitigated
    await db.commit()
    
    # =========================================
    # STEP 9: Create Incident Narrative (for RAG)
    # =========================================
    narrative = IncidentNarrative(
        incident_id=incident_id,
        time_range={
            "start": incident.detected_at.isoformat(),
            "end": datetime.utcnow().isoformat()
        },
        root_cause_hypothesis="Container exceeded memory limits, triggering OOM killer",
        confidence=0.85,
        evidence_refs=["docker://test-container/logs", "docker://test-container/stats"],
        resolution_steps=[{
            "action": "restart_resource",
            "target": "docker://test-container",
            "result": "success"
        }],
        verification_results={"container_running": True, "memory_usage_pct": 45},
        outcome="mitigated",
        lessons_learned="Consider increasing container memory limit or implementing memory monitoring alerts",
        narrative_text=(
            "High memory usage incident detected on docker://test-container. "
            "Container was killed by OOM killer. Remediation: restarted container. "
            "Container is now running with 45% memory usage. "
            "Recommendation: review memory limits for this container."
        )
    )
    db.add(narrative)
    await db.commit()
    await db.refresh(narrative)
    
    assert narrative.id is not None
    assert narrative.confidence == 0.85
    
    # =========================================
    # VERIFICATION: Complete Flow Integrity
    # =========================================
    # Re-fetch and verify final state
    result_incident = await db.get(Incident, incident_id)
    assert result_incident.status == IncidentStatus.mitigated
    
    result_todo = await db.get(TodoStep, todo.id)
    assert result_todo.status == ActionStatus.completed
    
    # Verify action history recorded
    action_query = select(ActionHistory).where(ActionHistory.incident_id == incident_id)
    actions = (await db.execute(action_query)).scalars().all()
    assert len(actions) == 1
    assert actions[0].status == ActionStatus.completed
    
    # Verify narrative exists
    narrative_query = select(IncidentNarrative).where(IncidentNarrative.incident_id == incident_id)
    narratives = (await db.execute(narrative_query)).scalars().all()
    assert len(narratives) == 1
    assert "OOM" in narratives[0].narrative_text


@pytest.mark.asyncio
async def test_plan_rejection_by_policy_denylist(clean_db):
    """Test that policy engine rejects plans targeting denylisted resources."""
    db = clean_db
    # Create a plan targeting denylisted resource
    proposal = PlanProposal(
        id="test-plan-deny",
        incident_id=None,
        title="Stop Storage Controller",
        description="Attempting to stop storage controller",
        created_at=datetime.utcnow(),
        steps=[
            PlanStep(
                order=1,
                action=ActionTemplate.stop_resource,
                target="docker://storage-controller"
            )
        ]
    )
    
    is_valid, violations = await policy_engine.validate(db, proposal)
    
    assert not is_valid
    assert len(violations) > 0
    assert any("DENYLIST" in v or "storage-controller" in v.lower() for v in violations)


@pytest.mark.asyncio
async def test_plan_rejection_by_rate_limit(clean_db):
    """Test that policy engine enforces rate limiting on repeated actions."""
    db = clean_db
    # Insert recent actions to trigger rate limit
    for i in range(3):
        action = ActionHistory(
            action_template=ActionTemplate.restart_resource,
            target_resource="docker://rate-limited-container",
            status=ActionStatus.completed,
            executed_at=datetime.utcnow()
        )
        db.add(action)
    await db.commit()
    
    # Now try to add another
    proposal = PlanProposal(
        id="test-plan-rate",
        incident_id=None,
        title="Rate Limited Restart",
        description="This should be rate limited",
        created_at=datetime.utcnow(),
        steps=[
            PlanStep(
                order=1,
                action=ActionTemplate.restart_resource,
                target="docker://rate-limited-container"
            )
        ]
    )
    
    is_valid, violations = await policy_engine.validate(db, proposal)
    
    assert not is_valid
    assert len(violations) > 0
    assert any("rate" in v.lower() or "limit" in v.lower() for v in violations)


@pytest.mark.asyncio
async def test_proxmox_execution_routing(clean_db):
    """Test that Proxmox execution routes through adapter methods."""
    from homelab.control_plane.executor_router import executor_router
    from homelab.control_plane.plan_proposal import PlanStep
    from homelab.storage.models import ActionTemplate
    
    # Create a step targeting Proxmox VM
    step = PlanStep(
        order=1,
        action=ActionTemplate.restart_resource,
        target="proxmox://pve1/qemu/100"
    )
    
    # Mock the proxmox adapter
    with patch('homelab.control_plane.executor_router.proxmox_adapter') as mock_proxmox:
        mock_proxmox.reboot_resource = AsyncMock(return_value=True)
        
        result = await executor_router.execute_step(step)
        
        assert result["success"] is True
        assert result["adapter"] == "proxmox"
        assert result["type"] == "vm"
        
        # Verify it called the adapter method with correct args
        mock_proxmox.reboot_resource.assert_called_once_with("pve1", "qemu", 100)


@pytest.mark.asyncio
async def test_proxmox_lxc_execution_routing(clean_db):
    """Test that Proxmox LXC execution routes through adapter methods."""
    from homelab.control_plane.executor_router import executor_router
    from homelab.control_plane.plan_proposal import PlanStep
    from homelab.storage.models import ActionTemplate
    
    # Create a step targeting Proxmox LXC
    step = PlanStep(
        order=1,
        action=ActionTemplate.restart_resource,
        target="proxmox://pve1/lxc/101"
    )
    
    with patch('homelab.control_plane.executor_router.proxmox_adapter') as mock_proxmox:
        mock_proxmox.reboot_resource = AsyncMock(return_value=True)
        
        result = await executor_router.execute_step(step)
        
        assert result["success"] is True
        assert result["adapter"] == "proxmox"
        assert result["type"] == "lxc"
        
        mock_proxmox.reboot_resource.assert_called_once_with("pve1", "lxc", 101)
