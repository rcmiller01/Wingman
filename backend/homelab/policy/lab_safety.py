"""LAB mode safety enforcement.

Ensures LAB mode:
1. Can ONLY be enabled via explicit environment variable
2. Fails closed without allowlists configured  
3. Provides visible warnings/banners for UI
4. Requires explicit opt-in for dangerous operations
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyViolation(Exception):
    """Raised when a safety policy is violated."""
    pass


class LabModeViolation(SafetyViolation):
    """Raised when LAB mode is used unsafely."""
    pass


@dataclass
class LabSafetyConfig:
    """Configuration for LAB mode safety."""
    
    # LAB mode can only be enabled via these env vars (fail-closed)
    required_env_var: str = "WINGMAN_EXECUTION_MODE"
    required_value: str = "lab"
    
    # Allowlists - must be non-empty in LAB mode
    container_allowlist: list[str] = field(default_factory=list)
    vm_allowlist: list[str] = field(default_factory=list)  # Proxmox VM IDs
    node_allowlist: list[str] = field(default_factory=list)  # Proxmox nodes
    
    # Dangerous operations require additional opt-in
    dangerous_ops_enabled: bool = False
    dangerous_ops_env_var: str = "WINGMAN_ALLOW_DANGEROUS_OPS"
    
    # Read-only mode - blocks all write operations
    read_only_mode: bool = False
    read_only_env_var: str = "WINGMAN_READ_ONLY"
    
    @classmethod
    def from_env(cls) -> "LabSafetyConfig":
        """Load LAB safety config from environment."""
        config = cls()
        
        # Load allowlists from comma-separated env vars
        container_list = os.environ.get("WINGMAN_CONTAINER_ALLOWLIST", "")
        if container_list:
            config.container_allowlist = [c.strip() for c in container_list.split(",") if c.strip()]
        
        vm_list = os.environ.get("WINGMAN_VM_ALLOWLIST", "")
        if vm_list:
            config.vm_allowlist = [v.strip() for v in vm_list.split(",") if v.strip()]
        
        node_list = os.environ.get("WINGMAN_NODE_ALLOWLIST", "")
        if node_list:
            config.node_allowlist = [n.strip() for n in node_list.split(",") if n.strip()]
        
        # Dangerous operations opt-in
        config.dangerous_ops_enabled = os.environ.get(
            config.dangerous_ops_env_var, ""
        ).lower() in ("true", "1", "yes")
        
        # Read-only mode
        config.read_only_mode = os.environ.get(
            config.read_only_env_var, ""
        ).lower() in ("true", "1", "yes")
        
        return config
    
    def has_any_allowlist(self) -> bool:
        """Check if any allowlist is configured."""
        return bool(
            self.container_allowlist or 
            self.vm_allowlist or 
            self.node_allowlist
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "container_allowlist": self.container_allowlist,
            "vm_allowlist": self.vm_allowlist,
            "node_allowlist": self.node_allowlist,
            "dangerous_ops_enabled": self.dangerous_ops_enabled,
            "read_only_mode": self.read_only_mode,
            "has_allowlists": self.has_any_allowlist(),
        }


class LabModeStatus(str, Enum):
    """Status of LAB mode safety."""
    SAFE = "safe"           # LAB mode properly configured
    ARMED = "armed"         # LAB mode armed and operational
    BLOCKED = "blocked"     # LAB mode requested but blocked (no allowlists)
    DISABLED = "disabled"   # LAB mode not requested


@dataclass
class LabSafetyStatus:
    """Current status of LAB mode safety."""
    
    status: LabModeStatus
    is_lab_mode: bool
    is_fail_safe: bool  # True if we're in a safe state
    allowlists_configured: bool
    dangerous_ops_available: bool
    read_only: bool
    
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    
    config: Optional[LabSafetyConfig] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "is_lab_mode": self.is_lab_mode,
            "is_fail_safe": self.is_fail_safe,
            "allowlists_configured": self.allowlists_configured,
            "dangerous_ops_available": self.dangerous_ops_available,
            "read_only": self.read_only,
            "warnings": self.warnings,
            "blockers": self.blockers,
            "config": self.config.to_dict() if self.config else None,
        }


class LabSafetyEnforcer:
    """Enforces LAB mode safety policies."""
    
    def __init__(self):
        self._config: Optional[LabSafetyConfig] = None
        self._status: Optional[LabSafetyStatus] = None
        self._last_check: Optional[datetime] = None
    
    @property
    def config(self) -> LabSafetyConfig:
        """Get or load safety config."""
        if self._config is None:
            self._config = LabSafetyConfig.from_env()
        return self._config
    
    def refresh_config(self) -> LabSafetyConfig:
        """Reload config from environment."""
        self._config = LabSafetyConfig.from_env()
        self._status = None  # Force status recalculation
        return self._config
    
    def is_lab_mode_requested(self) -> bool:
        """Check if LAB mode was explicitly requested via env var."""
        mode_value = os.environ.get(self.config.required_env_var, "").lower()
        return mode_value == self.config.required_value
    
    def validate_lab_mode(self) -> LabSafetyStatus:
        """
        Validate LAB mode can be safely enabled.
        
        LAB mode FAILS CLOSED:
        - Must be explicitly requested via WINGMAN_EXECUTION_MODE=lab
        - Must have at least one allowlist configured
        - Dangerous ops must be explicitly enabled
        """
        warnings = []
        blockers = []
        
        is_lab_requested = self.is_lab_mode_requested()
        config = self.config
        
        if not is_lab_requested:
            # Not requesting LAB mode - safe default
            return LabSafetyStatus(
                status=LabModeStatus.DISABLED,
                is_lab_mode=False,
                is_fail_safe=True,
                allowlists_configured=config.has_any_allowlist(),
                dangerous_ops_available=False,
                read_only=True,  # Non-lab modes are effectively read-only for real infra
                warnings=[],
                blockers=[],
                config=config,
            )
        
        # LAB mode requested - validate safety requirements
        if not config.has_any_allowlist():
            blockers.append(
                "LAB mode requested but no allowlists configured. "
                "Set WINGMAN_CONTAINER_ALLOWLIST, WINGMAN_VM_ALLOWLIST, or WINGMAN_NODE_ALLOWLIST."
            )
        
        # Check for dangerous operations
        if config.dangerous_ops_enabled:
            warnings.append(
                "⚠️ Dangerous operations enabled (WINGMAN_ALLOW_DANGEROUS_OPS=true). "
                "Prune, delete, and destructive operations are available."
            )
        
        # Determine final status
        if blockers:
            status = LabModeStatus.BLOCKED
            is_lab_mode = False
            is_fail_safe = True  # We're safe because we blocked it
            logger.warning(f"[LabSafety] LAB mode BLOCKED: {blockers}")
        else:
            status = LabModeStatus.ARMED
            is_lab_mode = True
            is_fail_safe = False  # We're in danger zone
            logger.info(f"[LabSafety] LAB mode ARMED with allowlists: {config.to_dict()}")
            if not warnings:
                warnings.append(
                    "🔴 LAB mode is ARMED. Operations will affect real infrastructure."
                )
        
        self._status = LabSafetyStatus(
            status=status,
            is_lab_mode=is_lab_mode,
            is_fail_safe=is_fail_safe,
            allowlists_configured=config.has_any_allowlist(),
            dangerous_ops_available=config.dangerous_ops_enabled,
            read_only=config.read_only_mode,
            warnings=warnings,
            blockers=blockers,
            config=config,
        )
        self._last_check = datetime.now(timezone.utc)
        
        return self._status
    
    def get_status(self) -> LabSafetyStatus:
        """Get current LAB safety status."""
        if self._status is None:
            return self.validate_lab_mode()
        return self._status
    
    def require_lab_mode(self) -> LabSafetyStatus:
        """
        Require LAB mode to be properly configured.
        
        Raises LabModeViolation if LAB mode is requested but not safe.
        """
        status = self.validate_lab_mode()
        
        if status.status == LabModeStatus.BLOCKED:
            raise LabModeViolation(
                f"LAB mode cannot be enabled: {'; '.join(status.blockers)}"
            )
        
        return status
    
    def check_target_allowed(
        self,
        target: str,
        target_type: str = "container",
    ) -> tuple[bool, str]:
        """
        Check if a target is in the allowlist.
        
        Returns (is_allowed, reason).
        """
        config = self.config
        
        if target_type == "container":
            if not config.container_allowlist:
                return False, "No containers in allowlist"
            
            # Check exact match or prefix match
            for allowed in config.container_allowlist:
                if target == allowed or target.startswith(allowed):
                    return True, f"Container '{target}' matches allowlist entry '{allowed}'"
            
            return False, f"Container '{target}' not in allowlist: {config.container_allowlist}"
        
        elif target_type == "vm":
            if not config.vm_allowlist:
                return False, "No VMs in allowlist"
            
            if target in config.vm_allowlist:
                return True, f"VM '{target}' in allowlist"
            
            return False, f"VM '{target}' not in allowlist: {config.vm_allowlist}"
        
        elif target_type == "node":
            if not config.node_allowlist:
                return False, "No nodes in allowlist"
            
            if target in config.node_allowlist:
                return True, f"Node '{target}' in allowlist"
            
            return False, f"Node '{target}' not in allowlist: {config.node_allowlist}"
        
        else:
            return False, f"Unknown target type: {target_type}"
    
    def check_operation_allowed(
        self,
        skill_id: str,
        target: str,
        target_type: str = "container",
    ) -> tuple[bool, str]:
        """
        Check if an operation is allowed in LAB mode.
        
        Returns (is_allowed, reason).
        """
        status = self.get_status()
        config = self.config
        
        # If not in LAB mode, block real operations
        if not status.is_lab_mode:
            return False, f"Not in LAB mode (status: {status.status.value})"
        
        # Check read-only mode
        if config.read_only_mode:
            # Only allow read-only operations
            if not self._is_read_only_skill(skill_id):
                return False, f"Read-only mode enabled, skill '{skill_id}' blocked"
        
        # Check if target is in allowlist
        target_allowed, target_reason = self.check_target_allowed(target, target_type)
        if not target_allowed:
            return False, target_reason
        
        # Check dangerous operations
        if self._is_dangerous_skill(skill_id):
            if not config.dangerous_ops_enabled:
                return False, f"Dangerous operation '{skill_id}' requires WINGMAN_ALLOW_DANGEROUS_OPS=true"
        
        return True, "Operation allowed"
    
    def _is_read_only_skill(self, skill_id: str) -> bool:
        """Check if a skill is read-only (safe in read-only mode)."""
        read_only_prefixes = (
            "diag-", "health-", "mon-", "inv-",
            "collect", "inspect", "list", "status", "check",
        )
        return any(skill_id.startswith(prefix) or prefix in skill_id for prefix in read_only_prefixes)
    
    def _is_dangerous_skill(self, skill_id: str) -> bool:
        """Check if a skill is dangerous (requires explicit opt-in)."""
        dangerous_patterns = (
            "prune", "delete", "remove", "destroy",
            "force", "rollback", "snapshot",
        )
        return any(pattern in skill_id.lower() for pattern in dangerous_patterns)
    
    def get_banner_message(self) -> Optional[str]:
        """Get banner message for UI display."""
        status = self.get_status()
        
        if status.status == LabModeStatus.ARMED:
            if status.dangerous_ops_available:
                return "🔴 LAB MODE ARMED - DANGEROUS OPS ENABLED - Real infrastructure affected"
            return "🔴 LAB MODE ARMED - Real infrastructure affected"
        
        if status.status == LabModeStatus.BLOCKED:
            return "⚠️ LAB MODE BLOCKED - Configure allowlists to enable"
        
        return None


# Singleton instance
lab_safety_enforcer = LabSafetyEnforcer()


def get_lab_safety_status() -> LabSafetyStatus:
    """Get current LAB safety status."""
    return lab_safety_enforcer.get_status()


def require_safe_lab_mode() -> LabSafetyStatus:
    """Require LAB mode to be safely configured."""
    return lab_safety_enforcer.require_lab_mode()


def check_lab_operation_allowed(
    skill_id: str,
    target: str,
    target_type: str = "container",
) -> tuple[bool, str]:
    """Check if an operation is allowed in current mode."""
    return lab_safety_enforcer.check_operation_allowed(skill_id, target, target_type)
