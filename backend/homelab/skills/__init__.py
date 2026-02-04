"""Skills Module - Executable runbooks with safety controls.

Skills are templated, auditable actions that can be executed against infrastructure.
They follow a tiered execution model:

- Tier 1 (Low Risk): Auto-approve, execute immediately
- Tier 2 (Medium Risk): Require human approval before execution  
- Tier 3 (High Risk): Require human approval + judge audit after execution

Each skill execution produces:
- Execution logs for debugging
- Audit artifact for compliance
- Optional retry on failure (max 1)
- Human escalation if retry fails
"""

from .registry import SkillRegistry, skill_registry
from .models import (
    Skill,
    SkillMeta,
    SkillCategory,
    SkillRisk,
    SkillExecution,
    SkillExecutionStatus,
)
from .runner import SkillRunner, skill_runner
from .execution_modes import (
    ExecutionMode,
    ExecutionModeManager,
    execution_mode_manager,
    MockResponse,
    execution_mode_context,
    async_execution_mode_context,
)

__all__ = [
    "SkillRegistry",
    "skill_registry",
    "Skill",
    "SkillMeta",
    "SkillCategory", 
    "SkillRisk",
    "SkillExecution",
    "SkillExecutionStatus",
    "SkillRunner",
    "skill_runner",
    # Execution modes
    "ExecutionMode",
    "ExecutionModeManager",
    "execution_mode_manager",
    "MockResponse",
    "execution_mode_context",
    "async_execution_mode_context",
]
