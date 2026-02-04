"""Runtime module - execution mode management and dependency wiring."""

from homelab.runtime.mode import (
    ExecutionMode,
    get_execution_mode,
    set_execution_mode,
    is_mock_mode,
    is_integration_mode,
    is_lab_mode,
)
from homelab.runtime.deps import (
    get_adapters,
    get_safety_policy,
    RuntimeDependencies,
)
from homelab.runtime.safety import (
    SafetyPolicy,
    MockSafetyPolicy,
    IntegrationSafetyPolicy,
    LabSafetyPolicy,
)
from homelab.runtime.policy_findings import (
    PolicyFinding,
    PolicyFindingLevel,
    PolicyFindingCode,
    PolicyDecision,
)

__all__ = [
    # Mode
    "ExecutionMode",
    "get_execution_mode",
    "set_execution_mode",
    "is_mock_mode",
    "is_integration_mode",
    "is_lab_mode",
    # Dependencies
    "get_adapters",
    "get_safety_policy",
    "RuntimeDependencies",
    # Safety
    "SafetyPolicy",
    "MockSafetyPolicy",
    "IntegrationSafetyPolicy",
    "LabSafetyPolicy",
    # Policy findings
    "PolicyFinding",
    "PolicyFindingLevel",
    "PolicyFindingCode",
    "PolicyDecision",
]
