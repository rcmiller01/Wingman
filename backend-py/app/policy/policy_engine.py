"""Policy engine for Guide Mode validation."""

from typing import Any
from app.control_plane.plan_proposal import PlanProposal, PlanStep, ActionType


# Safe actions that can be proposed
ALLOWED_ACTIONS = {
    ActionType.restart_container,
    ActionType.start_container,
    ActionType.stop_container,
    # Future: ActionType.restart_vm, etc.
}

# Maximum steps in a plan
MAX_PLAN_STEPS = 10

# Actions that require explicit confirmation
DANGEROUS_ACTIONS = {
    ActionType.stop_container,
    ActionType.stop_vm,
}


class PolicyViolation(Exception):
    """Raised when a plan violates policy."""
    def __init__(self, message: str, violations: list[str]):
        self.message = message
        self.violations = violations
        super().__init__(message)


class PolicyEngine:
    """Validates plan proposals against safety policies."""
    
    def validate(self, plan: PlanProposal) -> tuple[bool, list[str]]:
        """
        Validate a plan proposal.
        Returns (is_valid, list_of_violations).
        """
        violations = []
        
        # Check step count
        if len(plan.steps) > MAX_PLAN_STEPS:
            violations.append(f"Plan exceeds maximum steps ({MAX_PLAN_STEPS})")
        
        if len(plan.steps) == 0:
            violations.append("Plan has no steps")
        
        # Validate each step
        for step in plan.steps:
            step_violations = self._validate_step(step)
            violations.extend(step_violations)
        
        # Check for duplicate targets
        targets = [s.target for s in plan.steps]
        if len(targets) != len(set(targets)):
            violations.append("Plan contains duplicate targets (potential conflict)")
        
        return len(violations) == 0, violations
    
    def _validate_step(self, step: PlanStep) -> list[str]:
        """Validate a single plan step."""
        violations = []
        
        # Check action is allowed
        if step.action not in ALLOWED_ACTIONS:
            violations.append(f"Action '{step.action.value}' is not allowed")
        
        # Check target is specified
        if not step.target:
            violations.append(f"Step {step.order} has no target")
        
        # Validate target format
        if not step.target.startswith(("docker://", "proxmox://")):
            violations.append(f"Step {step.order} has invalid target format")
        
        return violations
    
    def check_dangerous(self, plan: PlanProposal) -> list[PlanStep]:
        """Return list of steps that require extra confirmation."""
        dangerous = []
        for step in plan.steps:
            if step.action in DANGEROUS_ACTIONS:
                dangerous.append(step)
        return dangerous
    
    def is_guide_mode_required(self) -> bool:
        """
        Check if guide mode is required.
        In the current implementation, guide mode is ALWAYS required.
        """
        return True


# Singleton
policy_engine = PolicyEngine()
