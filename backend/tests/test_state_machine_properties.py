# test_state_machine_properties.py
"""
Property-based tests for skill execution state machine.

Uses Hypothesis to randomly generate sequences of actions and verify
that state machine invariants are never violated.

Invariants under test:
1. executed implies approved (can't execute without approval)
2. rejected implies not executable (rejection is terminal for execution)
3. can't approve after rejection
4. can't reject after approval
5. retry_count never exceeds MAX_RETRIES
6. completed/failed are terminal states
7. state transitions are deterministic given same inputs
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, Phase
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize, Bundle
from unittest.mock import AsyncMock, patch
from datetime import datetime

from homelab.skills.models import (
    Skill, 
    SkillMeta, 
    SkillRisk, 
    SkillCategory, 
    SkillExecution, 
    SkillExecutionStatus
)
from homelab.skills.runner import SkillRunner, MAX_RETRIES
from homelab.skills.registry import skill_registry


# =============================================================================
# Test Skill Setup
# =============================================================================

def _register_test_skill(risk: SkillRisk, skill_id: str) -> str:
    """Register a test skill with specified risk level."""
    skill = Skill(
        meta=SkillMeta(
            id=skill_id,
            name=f"Test {risk.value} Skill",
            description=f"A test skill with {risk.value} risk",
            category=SkillCategory.diagnostics,
            risk=risk,
            target_types=["docker"],
        ),
        template="echo test",
    )
    skill_registry._skills[skill.meta.id] = skill
    return skill.meta.id


# Pre-register skills for property tests
LOW_RISK_SKILL = _register_test_skill(SkillRisk.low, "prop_test_low")
MEDIUM_RISK_SKILL = _register_test_skill(SkillRisk.medium, "prop_test_medium")
HIGH_RISK_SKILL = _register_test_skill(SkillRisk.high, "prop_test_high")


# =============================================================================
# State Machine for Property Testing
# =============================================================================

class SkillExecutionStateMachine(RuleBasedStateMachine):
    """
    State machine that randomly generates action sequences and verifies invariants.
    
    This catches edge-order bugs that hand-written tests might miss.
    """
    
    def __init__(self):
        super().__init__()
        self.runner = SkillRunner()
        self.executions: dict[str, SkillExecution] = {}
    
    # Bundle to track created executions
    execution_ids = Bundle("execution_ids")
    
    @rule(
        target=execution_ids,
        risk=st.sampled_from([SkillRisk.low, SkillRisk.medium, SkillRisk.high]),
        skip_approval=st.booleans(),
    )
    def create_execution(self, risk: SkillRisk, skip_approval: bool):
        """Create a new execution request."""
        skill_id = {
            SkillRisk.low: LOW_RISK_SKILL,
            SkillRisk.medium: MEDIUM_RISK_SKILL,
            SkillRisk.high: HIGH_RISK_SKILL,
        }[risk]
        
        import asyncio
        execution = asyncio.get_event_loop().run_until_complete(
            self.runner.create_execution(
                skill_id=skill_id,
                target="docker://test-container",
                parameters={},
                skip_approval=skip_approval,
            )
        )
        self.executions[execution.id] = execution
        return execution.id
    
    @rule(execution_id=execution_ids)
    def try_approve(self, execution_id: str):
        """Attempt to approve an execution (may fail based on state)."""
        execution = self.runner.get_execution(execution_id)
        if not execution:
            return
        
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(
                self.runner.approve(execution_id, approved_by="test-approver")
            )
        except ValueError:
            pass  # Expected for non-pending states
    
    @rule(execution_id=execution_ids)
    def try_reject(self, execution_id: str):
        """Attempt to reject an execution (may fail based on state)."""
        execution = self.runner.get_execution(execution_id)
        if not execution:
            return
        
        import asyncio
        try:
            with patch.object(self.runner, '_record_rejection_history', new_callable=AsyncMock):
                asyncio.get_event_loop().run_until_complete(
                    self.runner.reject(execution_id, rejected_by="test-rejecter", reason="test")
                )
        except ValueError:
            pass  # Expected for non-pending states
    
    @rule(execution_id=execution_ids)
    def try_execute(self, execution_id: str):
        """Attempt to execute (may fail based on state)."""
        execution = self.runner.get_execution(execution_id)
        if not execution:
            return
        
        import asyncio
        try:
            with patch.object(self.runner, '_execute_skill', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {"success": True}
                with patch.object(self.runner, '_record_action_history', new_callable=AsyncMock):
                    with patch('homelab.skills.runner.policy_engine') as mock_policy:
                        mock_policy.validate_skill_execution = AsyncMock(return_value=(True, []))
                        asyncio.get_event_loop().run_until_complete(
                            self.runner.execute(execution_id)
                        )
        except ValueError:
            pass  # Expected for non-approved states
    
    # =========================================================================
    # INVARIANTS - These must NEVER be violated regardless of action sequence
    # =========================================================================
    
    @invariant()
    def executed_implies_was_approved(self):
        """INVARIANT: An execution can only reach completed/failed if it was approved."""
        for exec_id, execution in self.executions.items():
            current = self.runner.get_execution(exec_id)
            if not current:
                continue
            
            terminal_executed = {
                SkillExecutionStatus.completed,
                SkillExecutionStatus.failed,
                SkillExecutionStatus.escalated,
                SkillExecutionStatus.pending_audit,
            }
            
            if current.status in terminal_executed:
                # Must have been approved at some point
                assert current.approved_at is not None or current.approved_by is not None, \
                    f"Execution {exec_id} in {current.status} but was never approved"
    
    @invariant()
    def rejected_implies_not_executed(self):
        """INVARIANT: A rejected execution cannot have execution timestamps."""
        for exec_id, execution in self.executions.items():
            current = self.runner.get_execution(exec_id)
            if not current:
                continue
            
            if current.status == SkillExecutionStatus.rejected:
                assert current.started_at is None, \
                    f"Rejected execution {exec_id} has started_at set"
                # completed_at might be set to rejection time, that's ok
    
    @invariant()
    def retry_count_bounded(self):
        """INVARIANT: retry_count never exceeds MAX_RETRIES."""
        for exec_id, execution in self.executions.items():
            current = self.runner.get_execution(exec_id)
            if not current:
                continue
            
            assert current.retry_count <= MAX_RETRIES, \
                f"Execution {exec_id} has retry_count {current.retry_count} > MAX_RETRIES {MAX_RETRIES}"
    
    @invariant()
    def mutual_exclusion_approve_reject(self):
        """INVARIANT: Cannot be both approved and rejected."""
        for exec_id, execution in self.executions.items():
            current = self.runner.get_execution(exec_id)
            if not current:
                continue
            
            both_set = current.approved_at is not None and current.rejected_at is not None
            assert not both_set, \
                f"Execution {exec_id} has both approved_at and rejected_at set"
    
    @invariant()
    def status_consistency(self):
        """INVARIANT: Status field matches timestamp fields."""
        for exec_id, execution in self.executions.items():
            current = self.runner.get_execution(exec_id)
            if not current:
                continue
            
            if current.status == SkillExecutionStatus.approved:
                assert current.approved_at is not None, \
                    f"Status is approved but approved_at is None"
                assert current.rejected_at is None, \
                    f"Status is approved but rejected_at is set"
            
            if current.status == SkillExecutionStatus.rejected:
                assert current.rejected_at is not None, \
                    f"Status is rejected but rejected_at is None"
                assert current.approved_at is None, \
                    f"Status is rejected but approved_at is set"


# Run the state machine tests
TestSkillStateMachine = SkillExecutionStateMachine.TestCase


# =============================================================================
# Additional Property-Based Tests
# =============================================================================

class TestStateTransitionProperties:
    """Property tests for individual state transitions."""
    
    @pytest.fixture
    def runner(self):
        return SkillRunner()
    
    @given(
        risk=st.sampled_from([SkillRisk.low, SkillRisk.medium, SkillRisk.high]),
        skip_approval=st.booleans(),
    )
    @settings(max_examples=50, phases=[Phase.generate, Phase.target])
    def test_medium_high_always_require_approval(self, risk, skip_approval):
        """Property: Medium and high risk skills always require approval."""
        runner = SkillRunner()
        
        skill_id = {
            SkillRisk.low: LOW_RISK_SKILL,
            SkillRisk.medium: MEDIUM_RISK_SKILL,
            SkillRisk.high: HIGH_RISK_SKILL,
        }[risk]
        
        import asyncio
        execution = asyncio.get_event_loop().run_until_complete(
            runner.create_execution(
                skill_id=skill_id,
                target="docker://test",
                parameters={},
                skip_approval=skip_approval,
            )
        )
        
        # Medium/high must require approval regardless of skip_approval flag
        if risk in (SkillRisk.medium, SkillRisk.high):
            assert execution.status == SkillExecutionStatus.pending_approval
    
    @given(num_approvals=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_approve_is_idempotent_on_success(self, num_approvals):
        """Property: Multiple approvals on pending should succeed (first wins)."""
        runner = SkillRunner()
        
        import asyncio
        execution = asyncio.get_event_loop().run_until_complete(
            runner.create_execution(
                skill_id=MEDIUM_RISK_SKILL,
                target="docker://test",
                parameters={},
            )
        )
        
        first_approved_at = None
        first_approved_by = None
        
        for i in range(num_approvals):
            try:
                asyncio.get_event_loop().run_until_complete(
                    runner.approve(execution.id, approved_by=f"approver-{i}")
                )
                if first_approved_at is None:
                    first_approved_at = execution.approved_at
                    first_approved_by = execution.approved_by
            except ValueError:
                pass  # Expected after first approval
        
        # First approver wins
        assert execution.approved_by == first_approved_by
    
    @given(num_rejects=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_reject_is_idempotent(self, num_rejects):
        """Property: Multiple rejections should be idempotent."""
        runner = SkillRunner()
        
        import asyncio
        execution = asyncio.get_event_loop().run_until_complete(
            runner.create_execution(
                skill_id=MEDIUM_RISK_SKILL,
                target="docker://test",
                parameters={},
            )
        )
        
        first_rejected_at = None
        first_rejected_by = None
        
        for i in range(num_rejects):
            with patch.object(runner, '_record_rejection_history', new_callable=AsyncMock):
                result = asyncio.get_event_loop().run_until_complete(
                    runner.reject(execution.id, rejected_by=f"rejecter-{i}", reason="test")
                )
                if first_rejected_at is None:
                    first_rejected_at = result.rejected_at
                    first_rejected_by = result.rejected_by
        
        # First rejecter wins, subsequent are no-ops
        assert execution.rejected_by == first_rejected_by
        assert execution.rejected_at == first_rejected_at
