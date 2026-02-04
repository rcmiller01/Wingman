"""Unified policy findings schema for safety checks.

Provides a structured way to represent policy decisions, warnings,
and blocks that can be displayed in the UI and audited.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class PolicyFindingLevel(str, Enum):
    """Severity level of a policy finding."""
    info = "info"       # Informational, no action needed
    warn = "warn"       # Warning, execution allowed but flagged
    block = "block"     # Blocked, execution denied


class PolicyFindingCode(str, Enum):
    """Standardized codes for policy findings.
    
    Using codes makes it easier to:
    - Translate to different languages
    - Build UI components that respond to specific codes
    - Track policy evolution over time
    """
    # Mock mode findings
    MOCK_MODE_ACTIVE = "MOCK_MODE_ACTIVE"
    
    # Integration mode findings
    INTEGRATION_PROXMOX_BLOCKED = "INTEGRATION_PROXMOX_BLOCKED"
    INTEGRATION_LABEL_MISSING = "INTEGRATION_LABEL_MISSING"
    INTEGRATION_LABEL_PRESENT = "INTEGRATION_LABEL_PRESENT"
    INTEGRATION_PRUNE_BLOCKED = "INTEGRATION_PRUNE_BLOCKED"
    INTEGRATION_PRUNE_ALLOWED = "INTEGRATION_PRUNE_ALLOWED"
    
    # Lab mode findings
    LAB_ALLOWLIST_HIT = "LAB_ALLOWLIST_HIT"
    LAB_ALLOWLIST_MISS = "LAB_ALLOWLIST_MISS"
    LAB_DANGEROUS_BLOCKED = "LAB_DANGEROUS_BLOCKED"
    LAB_DANGEROUS_ALLOWED = "LAB_DANGEROUS_ALLOWED"
    LAB_READ_ONLY_MODE = "LAB_READ_ONLY_MODE"
    LAB_SKILL_NOT_ALLOWLISTED = "LAB_SKILL_NOT_ALLOWLISTED"
    
    # General findings
    SKILL_READ_ONLY = "SKILL_READ_ONLY"
    SKILL_REQUIRES_APPROVAL = "SKILL_REQUIRES_APPROVAL"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    PARAMETER_INVALID = "PARAMETER_INVALID"


@dataclass
class PolicyFinding:
    """A single policy finding from a safety check.
    
    Attributes:
        level: Severity (info/warn/block)
        code: Machine-readable code for the finding
        message: Human-readable message
        details: Additional details safe to display
        rule: The policy rule that triggered this finding
        timestamp: When the finding was generated
    """
    level: PolicyFindingLevel
    code: PolicyFindingCode
    message: str
    details: dict = field(default_factory=dict)
    rule: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level.value,
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "rule": self.rule,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PolicyFinding":
        """Create from dictionary."""
        return cls(
            level=PolicyFindingLevel(data["level"]),
            code=PolicyFindingCode(data["code"]),
            message=data["message"],
            details=data.get("details", {}),
            rule=data.get("rule"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
    
    @classmethod
    def info(cls, code: PolicyFindingCode, message: str, **kwargs) -> "PolicyFinding":
        """Create an info-level finding."""
        return cls(level=PolicyFindingLevel.info, code=code, message=message, **kwargs)
    
    @classmethod
    def warn(cls, code: PolicyFindingCode, message: str, **kwargs) -> "PolicyFinding":
        """Create a warning-level finding."""
        return cls(level=PolicyFindingLevel.warn, code=code, message=message, **kwargs)
    
    @classmethod
    def block(cls, code: PolicyFindingCode, message: str, **kwargs) -> "PolicyFinding":
        """Create a block-level finding."""
        return cls(level=PolicyFindingLevel.block, code=code, message=message, **kwargs)


@dataclass
class PolicyDecision:
    """Complete policy decision for an execution.
    
    Contains all findings and the final allow/deny decision.
    """
    allowed: bool
    findings: list[PolicyFinding] = field(default_factory=list)
    mode: str = "mock"
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(f.level == PolicyFindingLevel.warn for f in self.findings)
    
    @property
    def has_blocks(self) -> bool:
        """Check if there are any blocks."""
        return any(f.level == PolicyFindingLevel.block for f in self.findings)
    
    @property
    def blocking_findings(self) -> list[PolicyFinding]:
        """Get all blocking findings."""
        return [f for f in self.findings if f.level == PolicyFindingLevel.block]
    
    @property
    def warning_findings(self) -> list[PolicyFinding]:
        """Get all warning findings."""
        return [f for f in self.findings if f.level == PolicyFindingLevel.warn]
    
    @property
    def info_findings(self) -> list[PolicyFinding]:
        """Get all info findings."""
        return [f for f in self.findings if f.level == PolicyFindingLevel.info]
    
    @property
    def primary_reason(self) -> str:
        """Get the primary reason for the decision."""
        if self.blocking_findings:
            return self.blocking_findings[0].message
        if self.warning_findings:
            return f"Allowed with {len(self.warning_findings)} warning(s)"
        return "Allowed by policy"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "allowed": self.allowed,
            "findings": [f.to_dict() for f in self.findings],
            "mode": self.mode,
            "checked_at": self.checked_at,
            "has_warnings": self.has_warnings,
            "has_blocks": self.has_blocks,
            "primary_reason": self.primary_reason,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PolicyDecision":
        """Create from dictionary."""
        return cls(
            allowed=data["allowed"],
            findings=[PolicyFinding.from_dict(f) for f in data.get("findings", [])],
            mode=data.get("mode", "mock"),
            checked_at=data.get("checked_at", datetime.now(timezone.utc).isoformat()),
        )
    
    @classmethod
    def allow(cls, mode: str, findings: list[PolicyFinding] = None) -> "PolicyDecision":
        """Create an allow decision."""
        return cls(allowed=True, mode=mode, findings=findings or [])
    
    @classmethod
    def deny(cls, mode: str, findings: list[PolicyFinding]) -> "PolicyDecision":
        """Create a deny decision."""
        return cls(allowed=False, mode=mode, findings=findings)


# Helper functions for common findings

def mock_mode_finding() -> PolicyFinding:
    """Finding for mock mode (all ops simulated)."""
    return PolicyFinding.info(
        code=PolicyFindingCode.MOCK_MODE_ACTIVE,
        message="Mock mode: All operations are simulated",
        rule="EXECUTION_MODE=mock",
    )


def integration_label_missing(container_id: str) -> PolicyFinding:
    """Finding for missing test container label."""
    return PolicyFinding.block(
        code=PolicyFindingCode.INTEGRATION_LABEL_MISSING,
        message=f"Container '{container_id}' missing wingman.test=true label",
        details={"container_id": container_id, "required_label": "wingman.test=true"},
        rule="Integration mode: Only containers with wingman.test=true label can be modified",
    )


def integration_label_present(container_id: str) -> PolicyFinding:
    """Finding for container with test label."""
    return PolicyFinding.info(
        code=PolicyFindingCode.INTEGRATION_LABEL_PRESENT,
        message=f"Container '{container_id}' has wingman.test=true label",
        details={"container_id": container_id},
        rule="Integration mode: Container label verified",
    )


def integration_proxmox_blocked() -> PolicyFinding:
    """Finding for blocked Proxmox access in integration mode."""
    return PolicyFinding.block(
        code=PolicyFindingCode.INTEGRATION_PROXMOX_BLOCKED,
        message="Proxmox operations are blocked in integration mode",
        rule="Integration mode: Proxmox access disabled",
    )


def integration_prune_blocked() -> PolicyFinding:
    """Finding for blocked prune operation."""
    return PolicyFinding.block(
        code=PolicyFindingCode.INTEGRATION_PRUNE_BLOCKED,
        message="Prune operations are blocked by default in integration mode",
        details={"env_var": "INTEGRATION_ALLOW_PRUNE"},
        rule="Set INTEGRATION_ALLOW_PRUNE=true to enable",
    )


def integration_prune_allowed() -> PolicyFinding:
    """Finding for allowed prune operation (with warning)."""
    return PolicyFinding.warn(
        code=PolicyFindingCode.INTEGRATION_PRUNE_ALLOWED,
        message="Prune operation allowed via INTEGRATION_ALLOW_PRUNE=true",
        details={"env_var": "INTEGRATION_ALLOW_PRUNE", "value": "true"},
        rule="Prune operations enabled by environment variable",
    )


def lab_allowlist_hit(target_type: str, target_id: str, pattern: str) -> PolicyFinding:
    """Finding for target matching allowlist."""
    return PolicyFinding.info(
        code=PolicyFindingCode.LAB_ALLOWLIST_HIT,
        message=f"Target '{target_id}' matches allowlist pattern '{pattern}'",
        details={"target_type": target_type, "target_id": target_id, "pattern": pattern},
        rule=f"LAB_{target_type.upper()}_ALLOWLIST contains matching pattern",
    )


def lab_allowlist_miss(target_type: str, target_id: str, env_var: str) -> PolicyFinding:
    """Finding for target not in allowlist."""
    return PolicyFinding.block(
        code=PolicyFindingCode.LAB_ALLOWLIST_MISS,
        message=f"Target '{target_id}' not in {env_var}",
        details={"target_type": target_type, "target_id": target_id, "env_var": env_var},
        rule=f"Add '{target_id}' to {env_var} to allow access",
    )


def lab_dangerous_blocked(skill_id: str) -> PolicyFinding:
    """Finding for blocked dangerous operation."""
    return PolicyFinding.block(
        code=PolicyFindingCode.LAB_DANGEROUS_BLOCKED,
        message=f"Dangerous skill '{skill_id}' blocked in lab mode",
        details={"skill_id": skill_id, "env_var": "LAB_DANGEROUS_OK"},
        rule="Set LAB_DANGEROUS_OK=true to enable dangerous operations",
    )


def lab_dangerous_allowed(skill_id: str) -> PolicyFinding:
    """Finding for allowed dangerous operation (with warning)."""
    return PolicyFinding.warn(
        code=PolicyFindingCode.LAB_DANGEROUS_ALLOWED,
        message=f"Dangerous skill '{skill_id}' allowed via LAB_DANGEROUS_OK=true",
        details={"skill_id": skill_id},
        rule="Dangerous operations enabled by environment variable",
    )


def lab_read_only_blocked(skill_id: str) -> PolicyFinding:
    """Finding for blocked non-read-only skill in read-only mode."""
    return PolicyFinding.block(
        code=PolicyFindingCode.LAB_READ_ONLY_MODE,
        message=f"Non-diagnostic skill '{skill_id}' blocked (LAB_READ_ONLY=true)",
        details={"skill_id": skill_id},
        rule="Lab is in read-only mode; only diagnostic skills allowed",
    )


def skill_read_only(skill_id: str) -> PolicyFinding:
    """Finding for read-only skill (always allowed)."""
    return PolicyFinding.info(
        code=PolicyFindingCode.SKILL_READ_ONLY,
        message=f"Skill '{skill_id}' is read-only (diagnostic)",
        details={"skill_id": skill_id},
        rule="Read-only skills are always allowed",
    )
