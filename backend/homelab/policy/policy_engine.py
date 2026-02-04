"""Policy engine for Guide Mode validation."""

from typing import Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from homelab.control_plane.plan_proposal import PlanProposal, PlanStep
from homelab.storage.models import ActionTemplate, ActionHistory


# Safe actions that can be proposed
ALLOWED_ACTIONS = {
    ActionTemplate.restart_resource,
    ActionTemplate.start_resource,
    ActionTemplate.stop_resource,
    ActionTemplate.collect_diagnostics,
    ActionTemplate.create_snapshot,
    # Future: extend to VM or LXC-specific templates
}

# Map skill IDs to action templates for policy validation
SKILL_TO_ACTION_MAP = {
    "rem-restart-container": ActionTemplate.restart_resource,
    "rem-restart-vm": ActionTemplate.restart_resource,
    "rem-restart-lxc": ActionTemplate.restart_resource,
    "rem-stop-container": ActionTemplate.stop_resource,
    "rem-stop-vm": ActionTemplate.stop_resource,
    "diag-container-logs": ActionTemplate.collect_diagnostics,
    "diag-container-inspect": ActionTemplate.collect_diagnostics,
    "diag-vm-status": ActionTemplate.collect_diagnostics,
    "maint-prune-images": ActionTemplate.collect_diagnostics,
    "maint-create-snapshot": ActionTemplate.create_snapshot,
}

# Maximum steps in a plan
MAX_PLAN_STEPS = 10

# Actions that require explicit confirmation
DANGEROUS_ACTIONS = {
    ActionTemplate.stop_resource,
}

# Resources that should never be touched automatically
DENIED_RESOURCES = {
    "docker://storage-controller",
    "proxmox://pve/lxc/100", # Example critical container
}

MAX_ACTIONS_PER_HOUR = 3


class PolicyViolation(Exception):
    """Raised when a plan violates policy."""
    def __init__(self, message: str, violations: list[str]):
        self.message = message
        self.violations = violations
        super().__init__(message)


class PolicyEngine:
    """Validates plan proposals against safety policies."""
    
    async def validate(self, db: AsyncSession, plan: PlanProposal) -> tuple[bool, list[str]]:
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
            
            # Rate Limiting Check
            if step.target:
                is_limited, limit_msg = await self._check_rate_limit(db, step.target, step.action)
                if is_limited:
                    violations.append(limit_msg)
        
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
        
        # Check Denylist
        if step.target in DENIED_RESOURCES:
            violations.append(f"Target '{step.target}' is in the DENYLIST")
        
        # Validate target format
        if not step.target.startswith(("docker://", "proxmox://")):
            violations.append(f"Step {step.order} has invalid target format")
        
        return violations
    
    async def _check_rate_limit(self, db: AsyncSession, target: str, action: ActionTemplate) -> tuple[bool, str | None]:
        """Check if action rate limit is exceeded for target."""
        # Check actions on this target in the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        query = select(func.count()).select_from(ActionHistory).where(
            ActionHistory.target_resource == target,
            ActionHistory.action_template == action,
            ActionHistory.executed_at >= one_hour_ago
        )
        
        result = await db.execute(query)
        count = result.scalar() or 0
        
        if count >= MAX_ACTIONS_PER_HOUR:
            return True, f"Rate limit exceeded for {target} ({count} actions in last hour)"
        
        return False, None
    
    def check_dangerous(self, plan: PlanProposal) -> list[PlanStep]:
        """Return list of steps that require extra confirmation."""
        dangerous = []
        for step in plan.steps:
            if step.action in DANGEROUS_ACTIONS:
                dangerous.append(step)
        return dangerous
    
    async def validate_skill_execution(
        self,
        db: AsyncSession,
        skill_id: str,
        target: str,
    ) -> tuple[bool, list[str]]:
        """
        Validate a skill execution against policy.
        
        This ensures skills cannot bypass control-plane safeguards.
        Uses the same rules as plan validation.
        
        Returns (is_valid, list_of_violations).
        """
        violations = []
        
        # Map skill to action template
        action = SKILL_TO_ACTION_MAP.get(skill_id)
        if action is None:
            # Unknown skill - allow but log warning
            pass
        elif action not in ALLOWED_ACTIONS:
            violations.append(f"Skill action '{action.value}' is not allowed by policy")
        
        # Check target is not on denylist
        if target in DENIED_RESOURCES:
            violations.append(f"Target '{target}' is in the DENYLIST - skill execution blocked")
        
        # Validate target format
        if not target.startswith(("docker://", "proxmox://")):
            violations.append(f"Invalid target format: {target}")
        
        # Check rate limiting
        if action:
            is_limited, limit_msg = await self._check_rate_limit(db, target, action)
            if is_limited:
                violations.append(limit_msg)
        
        return len(violations) == 0, violations
    
    def is_skill_dangerous(self, skill_id: str) -> bool:
        """Check if a skill maps to a dangerous action requiring extra confirmation."""
        action = SKILL_TO_ACTION_MAP.get(skill_id)
        return action in DANGEROUS_ACTIONS if action else False
    
    def is_guide_mode_required(self) -> bool:
        """
        Check if guide mode is required.
        In the current implementation, guide mode is ALWAYS required.
        """
        return True


# Singleton
policy_engine = PolicyEngine()
