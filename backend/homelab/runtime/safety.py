"""Safety policies for each execution mode.

Each mode has different safety constraints:
- MOCK: No restrictions (everything is fake anyway)
- INTEGRATION: Docker restricted to labeled containers, no dangerous ops
- LAB: Strict allowlists, dangerous ops blocked unless explicitly enabled
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from homelab.runtime.policy_findings import (
    PolicyFinding,
    PolicyFindingCode,
    PolicyFindingLevel,
    PolicyDecision,
    mock_mode_finding,
    integration_label_missing,
    integration_label_present,
    integration_proxmox_blocked,
    integration_prune_blocked,
    integration_prune_allowed,
    lab_allowlist_hit,
    lab_allowlist_miss,
    lab_dangerous_blocked,
    lab_dangerous_allowed,
    lab_read_only_blocked,
    skill_read_only,
)

logger = logging.getLogger(__name__)


@dataclass
class SafetyCheckResult:
    """Result of a safety policy check."""
    allowed: bool
    reason: str
    warnings: list[str] = field(default_factory=list)
    
    @classmethod
    def allow(cls, reason: str = "Allowed by policy") -> "SafetyCheckResult":
        return cls(allowed=True, reason=reason)
    
    @classmethod
    def deny(cls, reason: str) -> "SafetyCheckResult":
        return cls(allowed=False, reason=reason)
    
    @classmethod
    def allow_with_warning(cls, reason: str, warnings: list[str]) -> "SafetyCheckResult":
        return cls(allowed=True, reason=reason, warnings=warnings)


class SafetyPolicy(ABC):
    """Abstract base class for safety policies."""
    
    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return the mode name for logging."""
        pass
    
    @abstractmethod
    def check_skill_execution(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> SafetyCheckResult:
        """Check if a skill execution is allowed.
        
        Args:
            skill_id: The skill being executed
            target_type: Type of target (docker, proxmox, etc.)
            target_id: Identifier of the target resource
            parameters: Skill parameters
            
        Returns:
            SafetyCheckResult indicating if execution is allowed
        """
        pass
    
    @abstractmethod
    def check_target_access(
        self,
        target_type: str,
        target_id: str,
        operation: str,
    ) -> SafetyCheckResult:
        """Check if access to a target is allowed.
        
        Args:
            target_type: Type of target (docker, proxmox, etc.)
            target_id: Identifier of the target resource
            operation: The operation being performed (read, write, delete, etc.)
            
        Returns:
            SafetyCheckResult indicating if access is allowed
        """
        pass
    
    def get_policy_decision(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> PolicyDecision:
        """Get a structured policy decision with findings.
        
        This is the preferred method for getting policy decisions as it
        returns structured findings that can be displayed in the UI.
        
        Default implementation wraps check_skill_execution - subclasses
        can override for richer findings.
        """
        result = self.check_skill_execution(skill_id, target_type, target_id, parameters)
        
        findings = []
        if result.allowed:
            if result.warnings:
                for warning in result.warnings:
                    findings.append(PolicyFinding.warn(
                        code=PolicyFindingCode.SKILL_REQUIRES_APPROVAL,
                        message=warning,
                    ))
        else:
            findings.append(PolicyFinding.block(
                code=PolicyFindingCode.PARAMETER_INVALID,
                message=result.reason,
            ))
        
        return PolicyDecision(
            allowed=result.allowed,
            findings=findings,
            mode=self.mode_name,
        )
    
    def is_dangerous_skill(self, skill_id: str) -> bool:
        """Check if a skill is considered dangerous."""
        dangerous_patterns = [
            r".*prune.*",
            r".*delete.*",
            r".*destroy.*",
            r".*remove.*",
            r"rem-stop-.*",
            r"maint-system-prune",
            r"maint-rollback-snapshot",
        ]
        return any(re.match(pattern, skill_id, re.IGNORECASE) for pattern in dangerous_patterns)
    
    def is_read_only_skill(self, skill_id: str) -> bool:
        """Check if a skill is read-only (diagnostics/monitoring)."""
        return skill_id.startswith(("diag-", "mon-"))


class MockSafetyPolicy(SafetyPolicy):
    """Safety policy for mock mode - allows everything."""
    
    @property
    def mode_name(self) -> str:
        return "mock"
    
    def check_skill_execution(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> SafetyCheckResult:
        """Mock mode allows all skill executions."""
        return SafetyCheckResult.allow("Mock mode - all operations allowed")
    
    def check_target_access(
        self,
        target_type: str,
        target_id: str,
        operation: str,
    ) -> SafetyCheckResult:
        """Mock mode allows all target access."""
        return SafetyCheckResult.allow("Mock mode - all access allowed")
    
    def get_policy_decision(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> PolicyDecision:
        """Mock mode returns allow with info finding."""
        return PolicyDecision.allow(
            mode="mock",
            findings=[mock_mode_finding()],
        )


class IntegrationSafetyPolicy(SafetyPolicy):
    """Safety policy for integration mode.
    
    Constraints:
    - Docker operations only on containers labeled wingman.test=true
    - No prune unless target explicitly labeled and skill is in allowlist
    - Proxmox operations always denied (should use mock)
    """
    
    # Skills allowed on test-labeled containers
    ALLOWED_SKILLS = {
        # Diagnostics (always safe)
        "diag-container-logs",
        "diag-container-inspect",
        "diag-container-stats",
        "diag-container-top",
        "diag-container-health",
        "diag-container-diff",
        "diag-container-port",
        "diag-network-inspect",
        "diag-system-df",
        # Remediation (on test containers only)
        "rem-restart-container",
        "rem-start-container",
        "rem-stop-container",
        "rem-pause-container",
        "rem-unpause-container",
        # Monitoring
        "mon-container-events",
        "mon-system-events",
    }
    
    # Skills that can prune/delete (require explicit allowlist)
    PRUNE_SKILLS = {
        "maint-prune-images",
        "maint-prune-containers",
        "maint-prune-volumes",
        "maint-prune-networks",
        "maint-system-prune",
    }
    
    @property
    def mode_name(self) -> str:
        return "integration"
    
    def __init__(self):
        # Load additional allowed container patterns from env
        self._container_allowlist: list[re.Pattern] = []
        env_allowlist = os.environ.get("INTEGRATION_CONTAINER_ALLOWLIST", "")
        if env_allowlist:
            for pattern in env_allowlist.split(","):
                pattern = pattern.strip()
                if pattern:
                    try:
                        self._container_allowlist.append(re.compile(pattern))
                    except re.error as e:
                        logger.warning(f"[Safety] Invalid container allowlist pattern: {pattern}: {e}")
        
        # Check if prune operations are allowed
        self._allow_prune = os.environ.get("INTEGRATION_ALLOW_PRUNE", "").lower() in ("true", "1")
    
    def _is_test_container(self, container_id: str) -> bool:
        """Check if a container is a test container.
        
        A container is considered a test container if:
        1. Its name/id matches a pattern in the allowlist, OR
        2. It has the wingman.test=true label (checked at runtime)
        """
        # Check against allowlist patterns
        for pattern in self._container_allowlist:
            if pattern.match(container_id):
                return True
        
        # Default patterns for common test container naming
        default_test_patterns = [
            r"^test[-_].*",
            r".*[-_]test$",
            r"^wingman[-_]test[-_].*",
        ]
        for pattern in default_test_patterns:
            if re.match(pattern, container_id, re.IGNORECASE):
                return True
        
        return False
    
    def check_skill_execution(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> SafetyCheckResult:
        """Check if skill execution is allowed in integration mode."""
        
        # Proxmox operations always denied in integration mode
        if target_type == "proxmox":
            return SafetyCheckResult.deny(
                "Integration mode: Proxmox operations not allowed (use mock adapter)"
            )
        
        # Read-only skills always allowed
        if self.is_read_only_skill(skill_id):
            return SafetyCheckResult.allow("Read-only skill allowed")
        
        # Prune/system-wide skills require explicit opt-in
        if skill_id in self.PRUNE_SKILLS:
            if not self._allow_prune:
                return SafetyCheckResult.deny(
                    f"Integration mode: Prune skill '{skill_id}' blocked. "
                    "Set INTEGRATION_ALLOW_PRUNE=true to enable."
                )
            # Prune skills are system-wide, no container check needed
            return SafetyCheckResult.allow("Prune skill allowed (INTEGRATION_ALLOW_PRUNE=true)")
        
        # Docker operations require test container (for container-specific skills)
        if target_type == "docker":
            container = parameters.get("container", target_id)
            # Skip container check for system-wide operations (empty container)
            if container and not self._is_test_container(container):
                return SafetyCheckResult.deny(
                    f"Integration mode: Container '{container}' not in test allowlist. "
                    "Containers must match wingman.test=true label or allowlist pattern."
                )
        
        # Check skill is in allowed list
        if skill_id not in self.ALLOWED_SKILLS:
            return SafetyCheckResult.deny(
                f"Integration mode: Skill '{skill_id}' not in integration allowlist"
            )
        
        return SafetyCheckResult.allow("Skill allowed in integration mode")
    
    def check_target_access(
        self,
        target_type: str,
        target_id: str,
        operation: str,
    ) -> SafetyCheckResult:
        """Check if target access is allowed in integration mode."""
        
        if target_type == "proxmox":
            return SafetyCheckResult.deny(
                "Integration mode: Proxmox access not allowed"
            )
        
        if target_type == "docker":
            if operation in ("read", "inspect", "logs"):
                return SafetyCheckResult.allow("Read operations allowed")
            
            if not self._is_test_container(target_id):
                return SafetyCheckResult.deny(
                    f"Integration mode: Write access to '{target_id}' denied - not a test container"
                )
        
        return SafetyCheckResult.allow("Access allowed")
    
    def get_policy_decision(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> PolicyDecision:
        """Get structured policy decision for integration mode."""
        findings: list[PolicyFinding] = []
        
        # Proxmox operations always denied
        if target_type == "proxmox":
            findings.append(integration_proxmox_blocked())
            return PolicyDecision.deny(mode="integration", findings=findings)
        
        # Read-only skills always allowed
        if self.is_read_only_skill(skill_id):
            findings.append(skill_read_only(skill_id))
            return PolicyDecision.allow(mode="integration", findings=findings)
        
        # Prune skills require explicit opt-in
        if skill_id in self.PRUNE_SKILLS:
            if not self._allow_prune:
                findings.append(integration_prune_blocked())
                return PolicyDecision.deny(mode="integration", findings=findings)
            findings.append(integration_prune_allowed())
            return PolicyDecision.allow(mode="integration", findings=findings)
        
        # Check container allowlist
        if target_type == "docker":
            container = parameters.get("container", target_id)
            if container:
                if self._is_test_container(container):
                    findings.append(integration_label_present(container))
                else:
                    findings.append(integration_label_missing(container))
                    return PolicyDecision.deny(mode="integration", findings=findings)
        
        # Check skill is in allowed list
        if skill_id not in self.ALLOWED_SKILLS:
            findings.append(PolicyFinding.block(
                code=PolicyFindingCode.SKILL_NOT_ALLOWLISTED if hasattr(PolicyFindingCode, 'SKILL_NOT_ALLOWLISTED') else PolicyFindingCode.PARAMETER_INVALID,
                message=f"Skill '{skill_id}' not in integration allowlist",
                rule="Only skills in ALLOWED_SKILLS can be executed in integration mode",
            ))
            return PolicyDecision.deny(mode="integration", findings=findings)
        
        return PolicyDecision.allow(mode="integration", findings=findings)


class LabSafetyPolicy(SafetyPolicy):
    """Safety policy for lab mode.
    
    Constraints:
    - Target allowlist (exact node/resource IDs or regex)
    - Read-only skills default unless explicitly whitelisted
    - Dangerous skills blocked unless LAB_DANGEROUS_OK=true
    """
    
    def __init__(self):
        # Load target allowlists from environment
        self._node_allowlist = self._load_allowlist("LAB_NODE_ALLOWLIST")
        self._vm_allowlist = self._load_allowlist("LAB_VM_ALLOWLIST")
        self._container_allowlist = self._load_allowlist("LAB_CONTAINER_ALLOWLIST")
        
        # Load skill allowlist (skills that can write)
        self._skill_allowlist = self._load_skill_allowlist()
        
        # Check if dangerous operations are explicitly allowed
        self._dangerous_ok = os.environ.get("LAB_DANGEROUS_OK", "").lower() in ("true", "1")
        
        # Read-only mode flag
        self._read_only = os.environ.get("LAB_READ_ONLY", "").lower() in ("true", "1")
        
        if self._dangerous_ok:
            logger.warning("[Safety] LAB_DANGEROUS_OK=true - dangerous operations enabled!")
    
    def _load_allowlist(self, env_var: str) -> list[re.Pattern]:
        """Load an allowlist from an environment variable."""
        patterns = []
        value = os.environ.get(env_var, "")
        if value:
            for pattern in value.split(","):
                pattern = pattern.strip()
                if pattern:
                    try:
                        # Support both exact match and regex
                        # Treat as regex if: starts with ^, ends with $, or contains regex chars
                        is_regex = (
                            pattern.startswith("^") or 
                            pattern.endswith("$") or
                            ".*" in pattern or
                            ".+" in pattern or
                            "[" in pattern
                        )
                        if is_regex:
                            # Ensure anchored for safety
                            if not pattern.startswith("^"):
                                pattern = "^" + pattern
                            if not pattern.endswith("$"):
                                pattern = pattern + "$"
                            patterns.append(re.compile(pattern))
                        else:
                            # Exact match
                            patterns.append(re.compile(f"^{re.escape(pattern)}$"))
                    except re.error as e:
                        logger.warning(f"[Safety] Invalid {env_var} pattern: {pattern}: {e}")
        return patterns
    
    def _load_skill_allowlist(self) -> set[str]:
        """Load skill allowlist from environment."""
        allowlist = set()
        value = os.environ.get("LAB_SKILL_ALLOWLIST", "")
        if value:
            for skill in value.split(","):
                skill = skill.strip()
                if skill:
                    allowlist.add(skill)
        return allowlist
    
    def _is_target_allowed(self, target_type: str, target_id: str) -> bool:
        """Check if a target is in the allowlist."""
        if target_type == "proxmox":
            # Check node allowlist for VMs/LXCs
            for pattern in self._node_allowlist + self._vm_allowlist:
                if pattern.match(target_id):
                    return True
        elif target_type == "docker":
            for pattern in self._container_allowlist:
                if pattern.match(target_id):
                    return True
        
        return False
    
    @property
    def mode_name(self) -> str:
        return "lab"
    
    def check_skill_execution(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> SafetyCheckResult:
        """Check if skill execution is allowed in lab mode."""
        
        # Read-only mode: only allow diagnostic/monitoring skills
        if self._read_only and not self.is_read_only_skill(skill_id):
            return SafetyCheckResult.deny(
                f"Lab mode (read-only): Non-diagnostic skill '{skill_id}' blocked"
            )
        
        # Read-only skills are always allowed (no target allowlist check needed)
        if self.is_read_only_skill(skill_id):
            return SafetyCheckResult.allow("Read-only skill allowed in lab mode")
        
        # Dangerous skills require explicit opt-in
        if self.is_dangerous_skill(skill_id) and not self._dangerous_ok:
            return SafetyCheckResult.deny(
                f"Lab mode: Dangerous skill '{skill_id}' blocked. "
                "Set LAB_DANGEROUS_OK=true to enable."
            )
        
        # Check target allowlist (skip for system-wide operations)
        if target_id and not self._is_target_allowed(target_type, target_id):
            return SafetyCheckResult.deny(
                f"Lab mode: Target '{target_id}' not in allowlist for type '{target_type}'"
            )
        
        # Non-read-only skills require explicit allowlist
        if not self.is_read_only_skill(skill_id):
            if self._skill_allowlist and skill_id not in self._skill_allowlist:
                return SafetyCheckResult.deny(
                    f"Lab mode: Skill '{skill_id}' not in LAB_SKILL_ALLOWLIST"
                )
        
        # Generate warnings for potentially risky operations
        warnings = []
        if self.is_dangerous_skill(skill_id):
            warnings.append(f"Executing dangerous skill '{skill_id}' in lab mode")
        if target_type == "proxmox":
            warnings.append(f"Operating on Proxmox target: {target_id}")
        
        if warnings:
            return SafetyCheckResult.allow_with_warning(
                "Skill allowed with warnings", warnings
            )
        
        return SafetyCheckResult.allow("Skill allowed in lab mode")
    
    def check_target_access(
        self,
        target_type: str,
        target_id: str,
        operation: str,
    ) -> SafetyCheckResult:
        """Check if target access is allowed in lab mode."""
        
        # Read operations always allowed
        if operation in ("read", "inspect", "logs", "status"):
            return SafetyCheckResult.allow("Read operations always allowed")
        
        # Check target allowlist
        if not self._is_target_allowed(target_type, target_id):
            return SafetyCheckResult.deny(
                f"Lab mode: Target '{target_id}' not in allowlist"
            )
        
        # Read-only mode blocks writes
        if self._read_only and operation not in ("read", "inspect", "logs", "status"):
            return SafetyCheckResult.deny(
                f"Lab mode (read-only): Write operation '{operation}' blocked"
            )
        
        return SafetyCheckResult.allow("Access allowed in lab mode")
    
    def get_policy_decision(
        self,
        skill_id: str,
        target_type: str,
        target_id: str,
        parameters: dict,
    ) -> PolicyDecision:
        """Get structured policy decision for lab mode."""
        findings: list[PolicyFinding] = []
        
        # Read-only mode check
        if self._read_only and not self.is_read_only_skill(skill_id):
            findings.append(lab_read_only_blocked(skill_id))
            return PolicyDecision.deny(mode="lab", findings=findings)
        
        # Read-only skills always allowed
        if self.is_read_only_skill(skill_id):
            findings.append(skill_read_only(skill_id))
            return PolicyDecision.allow(mode="lab", findings=findings)
        
        # Dangerous skills require explicit opt-in
        if self.is_dangerous_skill(skill_id):
            if not self._dangerous_ok:
                findings.append(lab_dangerous_blocked(skill_id))
                return PolicyDecision.deny(mode="lab", findings=findings)
            findings.append(lab_dangerous_allowed(skill_id))
        
        # Check target allowlist
        if target_id:
            env_var = f"LAB_{target_type.upper()}_ALLOWLIST"
            if target_type == "proxmox":
                env_var = "LAB_VM_ALLOWLIST or LAB_NODE_ALLOWLIST"
            
            if self._is_target_allowed(target_type, target_id):
                # Find which pattern matched
                matched_pattern = self._find_matching_pattern(target_type, target_id)
                findings.append(lab_allowlist_hit(target_type, target_id, matched_pattern or "*"))
            else:
                findings.append(lab_allowlist_miss(target_type, target_id, env_var))
                return PolicyDecision.deny(mode="lab", findings=findings)
        
        # Check skill allowlist if configured
        if self._skill_allowlist and skill_id not in self._skill_allowlist:
            findings.append(PolicyFinding.block(
                code=PolicyFindingCode.LAB_SKILL_NOT_ALLOWLISTED,
                message=f"Skill '{skill_id}' not in LAB_SKILL_ALLOWLIST",
                details={"skill_id": skill_id},
                rule="Add skill to LAB_SKILL_ALLOWLIST to allow execution",
            ))
            return PolicyDecision.deny(mode="lab", findings=findings)
        
        return PolicyDecision.allow(mode="lab", findings=findings)
    
    def _find_matching_pattern(self, target_type: str, target_id: str) -> str | None:
        """Find which allowlist pattern matched the target."""
        patterns = []
        if target_type == "proxmox":
            patterns = self._node_allowlist + self._vm_allowlist
        elif target_type == "docker":
            patterns = self._container_allowlist
        
        for pattern in patterns:
            if pattern.match(target_id):
                return pattern.pattern
        return None


def get_safety_policy_for_mode(mode: "ExecutionMode") -> SafetyPolicy:
    """Get the appropriate safety policy for a mode."""
    from homelab.runtime.mode import ExecutionMode
    
    policies = {
        ExecutionMode.mock: MockSafetyPolicy,
        ExecutionMode.integration: IntegrationSafetyPolicy,
        ExecutionMode.lab: LabSafetyPolicy,
    }
    
    policy_class = policies.get(mode, MockSafetyPolicy)
    return policy_class()
