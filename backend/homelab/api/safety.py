"""Safety API - expose safety policy status and allowlists.

Provides read-only visibility into:
- Current execution mode
- Active allowlists (lab mode)
- Why a target was blocked
- Policy configuration status
"""

import os
import re
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from homelab.runtime import (
    ExecutionMode,
    get_execution_mode,
    get_safety_policy,
    PolicyDecision,
)
from homelab.auth import (
    User,
    Permission,
    get_current_user,
    require_permission,
)
from homelab.config import get_settings

router = APIRouter(prefix="/api/safety", tags=["safety"])


# --- Response Models ---

class AllowlistEntry(BaseModel):
    """A single allowlist entry/pattern."""
    pattern: str
    type: str  # exact, regex
    source: str  # env var name


class AllowlistInfo(BaseModel):
    """Information about an allowlist."""
    name: str
    env_var: str
    entries: List[AllowlistEntry]
    count: int
    is_empty: bool


class SafetyModeInfo(BaseModel):
    """Information about the current safety mode."""
    mode: str
    is_mock: bool
    is_integration: bool
    is_lab: bool
    description: str
    # Flags
    dangerous_ok: bool = False
    read_only: bool = False
    prune_enabled: bool = False


class SafetyStatusResponse(BaseModel):
    """Full safety status response."""
    mode: SafetyModeInfo
    allowlists: List[AllowlistInfo]
    warnings: List[str]


class TargetCheckRequest(BaseModel):
    """Request to check if a target is allowed."""
    target_type: str  # docker, proxmox
    target_id: str
    operation: str = "access"


class TargetCheckResponse(BaseModel):
    """Response for target check."""
    allowed: bool
    reason: str
    matched_allowlist: Optional[str] = None
    matched_pattern: Optional[str] = None
    suggestions: List[str] = []


# --- Helper Functions ---

def _parse_allowlist_patterns(env_var: str) -> List[AllowlistEntry]:
    """Parse allowlist patterns from an environment variable."""
    entries = []
    value = os.environ.get(env_var, "")
    if value:
        for pattern in value.split(","):
            pattern = pattern.strip()
            if pattern:
                # Detect if it's a regex pattern
                is_regex = (
                    pattern.startswith("^") or 
                    pattern.endswith("$") or
                    ".*" in pattern or
                    ".+" in pattern or
                    "[" in pattern
                )
                entries.append(AllowlistEntry(
                    pattern=pattern,
                    type="regex" if is_regex else "exact",
                    source=env_var,
                ))
    return entries


def _get_mode_description(mode: ExecutionMode) -> str:
    """Get human-readable description of a mode."""
    descriptions = {
        ExecutionMode.MOCK: "All operations are simulated. Safe for development and testing.",
        ExecutionMode.INTEGRATION: "Docker operations on labeled test containers only. No Proxmox access.",
        ExecutionMode.LAB: "Real operations on allowlisted targets. Dangerous operations require opt-in.",
    }
    return descriptions.get(mode, "Unknown mode")


# --- Endpoints ---

@router.get("/status", response_model=SafetyStatusResponse)
async def get_safety_status(
    user: Optional[User] = Depends(get_current_user),
):
    """Get current safety mode and allowlist status.
    
    Returns information about:
    - Current execution mode
    - Active allowlists and their entries
    - Safety warnings and flags
    """
    mode = get_execution_mode()
    
    # Build mode info
    mode_info = SafetyModeInfo(
        mode=mode.value,
        is_mock=mode == ExecutionMode.MOCK,
        is_integration=mode == ExecutionMode.INTEGRATION,
        is_lab=mode == ExecutionMode.LAB,
        description=_get_mode_description(mode),
        dangerous_ok=os.environ.get("LAB_DANGEROUS_OK", "").lower() in ("true", "1"),
        read_only=os.environ.get("LAB_READ_ONLY", "").lower() in ("true", "1"),
        prune_enabled=os.environ.get("INTEGRATION_PRUNE_OK", "").lower() in ("true", "1"),
    )
    
    # Build allowlists based on mode
    allowlists = []
    warnings = []
    
    if mode == ExecutionMode.INTEGRATION:
        # Integration mode allowlists
        container_entries = _parse_allowlist_patterns("INTEGRATION_CONTAINER_ALLOWLIST")
        allowlists.append(AllowlistInfo(
            name="Integration Container Allowlist",
            env_var="INTEGRATION_CONTAINER_ALLOWLIST",
            entries=container_entries,
            count=len(container_entries),
            is_empty=len(container_entries) == 0,
        ))
        
        if not container_entries:
            warnings.append(
                "No container allowlist patterns set. "
                "Only containers with wingman.test=true label will be accessible."
            )
    
    elif mode == ExecutionMode.LAB:
        # Lab mode allowlists
        allowlist_configs = [
            ("Node Allowlist", "LAB_NODE_ALLOWLIST"),
            ("VM Allowlist", "LAB_VM_ALLOWLIST"),
            ("Container Allowlist", "LAB_CONTAINER_ALLOWLIST"),
        ]
        
        for name, env_var in allowlist_configs:
            entries = _parse_allowlist_patterns(env_var)
            allowlists.append(AllowlistInfo(
                name=name,
                env_var=env_var,
                entries=entries,
                count=len(entries),
                is_empty=len(entries) == 0,
            ))
        
        # Skill allowlist is special (comma-separated names, not patterns)
        skill_entries = []
        skill_value = os.environ.get("LAB_SKILL_ALLOWLIST", "")
        if skill_value:
            for skill in skill_value.split(","):
                skill = skill.strip()
                if skill:
                    skill_entries.append(AllowlistEntry(
                        pattern=skill,
                        type="exact",
                        source="LAB_SKILL_ALLOWLIST",
                    ))
        
        allowlists.append(AllowlistInfo(
            name="Skill Allowlist",
            env_var="LAB_SKILL_ALLOWLIST",
            entries=skill_entries,
            count=len(skill_entries),
            is_empty=len(skill_entries) == 0,
        ))
        
        # Add warnings
        empty_allowlists = [a for a in allowlists if a.is_empty]
        if empty_allowlists:
            warnings.append(
                f"Empty allowlists: {', '.join(a.name for a in empty_allowlists)}. "
                "No targets will be accessible for these types."
            )
        
        if mode_info.dangerous_ok:
            warnings.append("LAB_DANGEROUS_OK is enabled - dangerous operations allowed!")
        
        if mode_info.read_only:
            warnings.append("LAB_READ_ONLY is enabled - only diagnostic operations allowed.")
    
    return SafetyStatusResponse(
        mode=mode_info,
        allowlists=allowlists,
        warnings=warnings,
    )


@router.post("/check-target", response_model=TargetCheckResponse)
async def check_target_access(
    request: TargetCheckRequest,
    user: Optional[User] = Depends(get_current_user),
):
    """Check if a specific target would be allowed.
    
    This helps diagnose "why won't it run?" issues by checking
    a target against the current allowlists.
    """
    mode = get_execution_mode()
    policy = get_safety_policy()
    
    # Check via policy
    result = policy.check_target_access(
        target_type=request.target_type,
        target_id=request.target_id,
        operation=request.operation,
    )
    
    response = TargetCheckResponse(
        allowed=result.allowed,
        reason=result.reason,
        suggestions=[],
    )
    
    # Try to determine which allowlist/pattern matched
    if result.allowed:
        if mode == ExecutionMode.INTEGRATION:
            # Check if it's a labeled container or matches allowlist
            for entry in _parse_allowlist_patterns("INTEGRATION_CONTAINER_ALLOWLIST"):
                try:
                    if re.match(entry.pattern, request.target_id):
                        response.matched_allowlist = "INTEGRATION_CONTAINER_ALLOWLIST"
                        response.matched_pattern = entry.pattern
                        break
                except re.error:
                    pass
            
            if not response.matched_pattern:
                response.matched_allowlist = "wingman.test=true label"
                response.matched_pattern = "(container has test label)"
        
        elif mode == ExecutionMode.LAB:
            # Check which lab allowlist matched
            env_vars = {
                "proxmox": ["LAB_NODE_ALLOWLIST", "LAB_VM_ALLOWLIST"],
                "docker": ["LAB_CONTAINER_ALLOWLIST"],
            }
            
            for env_var in env_vars.get(request.target_type, []):
                for entry in _parse_allowlist_patterns(env_var):
                    try:
                        pattern = entry.pattern
                        # Ensure anchored
                        if not pattern.startswith("^"):
                            pattern = "^" + pattern
                        if not pattern.endswith("$"):
                            pattern = pattern + "$"
                        if re.match(pattern, request.target_id):
                            response.matched_allowlist = env_var
                            response.matched_pattern = entry.pattern
                            break
                    except re.error:
                        pass
    else:
        # Provide suggestions for blocked targets
        if mode == ExecutionMode.INTEGRATION:
            response.suggestions = [
                f"Add label wingman.test=true to the container",
                f"Add '{request.target_id}' to INTEGRATION_CONTAINER_ALLOWLIST",
            ]
        elif mode == ExecutionMode.LAB:
            if request.target_type == "proxmox":
                response.suggestions = [
                    f"Add '{request.target_id}' to LAB_VM_ALLOWLIST",
                    f"Add a regex pattern like '{request.target_id[:3]}.*' to LAB_VM_ALLOWLIST",
                ]
            elif request.target_type == "docker":
                response.suggestions = [
                    f"Add '{request.target_id}' to LAB_CONTAINER_ALLOWLIST",
                    f"Add a regex pattern to LAB_CONTAINER_ALLOWLIST",
                ]
        elif mode == ExecutionMode.MOCK:
            response.suggestions = [
                "Mock mode allows all targets - this should not happen",
            ]
    
    return response


@router.get("/allowlists")
async def list_allowlists(
    user: Optional[User] = Depends(get_current_user),
):
    """List all configured allowlists with their entries.
    
    This provides a quick overview of what's allowed in each mode.
    """
    mode = get_execution_mode()
    
    # All possible allowlists with their modes
    all_allowlists = {
        "integration": [
            ("INTEGRATION_CONTAINER_ALLOWLIST", "Containers allowed in integration mode"),
        ],
        "lab": [
            ("LAB_NODE_ALLOWLIST", "Proxmox nodes allowed in lab mode"),
            ("LAB_VM_ALLOWLIST", "VMs/LXCs allowed in lab mode"),
            ("LAB_CONTAINER_ALLOWLIST", "Docker containers allowed in lab mode"),
            ("LAB_SKILL_ALLOWLIST", "Skills that can perform writes in lab mode"),
        ],
    }
    
    result = {
        "current_mode": mode.value,
        "applicable_allowlists": [],
        "all_allowlists": {},
    }
    
    # Get applicable allowlists for current mode
    mode_key = mode.value.lower()
    if mode_key in all_allowlists:
        for env_var, description in all_allowlists[mode_key]:
            entries = _parse_allowlist_patterns(env_var)
            result["applicable_allowlists"].append({
                "env_var": env_var,
                "description": description,
                "entries": [e.dict() for e in entries],
                "count": len(entries),
                "is_empty": len(entries) == 0,
            })
    
    # Also show all allowlists for reference
    for mode_name, allowlists in all_allowlists.items():
        result["all_allowlists"][mode_name] = []
        for env_var, description in allowlists:
            value = os.environ.get(env_var, "")
            result["all_allowlists"][mode_name].append({
                "env_var": env_var,
                "description": description,
                "raw_value": value if value else "(not set)",
                "is_set": bool(value),
            })
    
    return result
