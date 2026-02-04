"""Executions API - skill execution management and lifecycle."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from homelab.skills import (
    skill_registry,
    skill_runner,
    SkillCategory,
    SkillRisk,
    SkillExecutionStatus,
)

# Use the new runtime module for mode management and safety
from homelab.runtime import (
    ExecutionMode,
    get_execution_mode,
    is_mock_mode,
    is_integration_mode,
    is_lab_mode,
    get_safety_policy,
    PolicyDecision,
    PolicyFinding,
)

# Auth support (optional - respects auth_enabled config)
from homelab.auth import (
    User,
    Permission,
    get_current_user,
    require_permission,
    get_approval_permission_for_risk,
    get_execute_permission_for_risk,
    user_context,
)
from homelab.config import get_settings

router = APIRouter(prefix="/api/executions", tags=["executions"])
logger = logging.getLogger(__name__)


def _get_optional_user():
    """Dependency that returns user if auth is enabled, None otherwise."""
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    # This will be overridden by the actual dependency at runtime
    return None


# --- Response Models ---

class PolicyFindingResponse(BaseModel):
    """A single policy finding."""
    level: str  # info, warn, block
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    rule: Optional[str] = None
    timestamp: str


class PolicyDecisionResponse(BaseModel):
    """Policy decision for an execution."""
    allowed: bool
    findings: list[PolicyFindingResponse] = []
    mode: str
    checked_at: str
    has_warnings: bool = False
    has_blocks: bool = False
    primary_reason: str = ""


class SkillMetaResponse(BaseModel):
    """Skill metadata for API responses."""
    id: str
    name: str
    description: str
    category: str
    risk: str
    target_types: list[str]
    required_params: list[str] = []
    optional_params: list[str] = []
    estimated_duration_seconds: int
    tags: list[str] = []
    requires_confirmation: bool = False


class ExecutionResponse(BaseModel):
    """Response for a skill execution record."""
    id: str
    skill_id: str
    skill_name: str
    status: str
    risk_level: str
    parameters: dict
    created_at: str
    updated_at: str
    # Mode and policy tracking
    execution_mode: str = "mock"
    policy_decision: Optional[PolicyDecisionResponse] = None
    # Approval tracking
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[str] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    # Execution tracking
    executed_at: Optional[str] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    # Target info
    target_type: Optional[str] = None
    target_id: Optional[str] = None


class ExecutionListResponse(BaseModel):
    """Response for listing executions."""
    executions: list[ExecutionResponse]
    total: int
    page: int
    page_size: int


class SkillCatalogResponse(BaseModel):
    """Response for listing available skills."""
    skills: list[SkillMetaResponse]
    categories: list[str]
    total: int


class CreateExecutionRequest(BaseModel):
    """Request to create a new skill execution."""
    skill_id: str
    parameters: dict = Field(default_factory=dict)
    target_type: Optional[str] = None  # docker, proxmox
    target_id: Optional[str] = None  # container name, vm id, etc.
    skip_approval: bool = False  # Only works for low-risk skills


class PreviewExecutionRequest(BaseModel):
    """Request to preview an execution before creating it."""
    skill_id: str
    parameters: dict = Field(default_factory=dict)
    target_type: Optional[str] = None
    target_id: Optional[str] = None


class PreviewExecutionResponse(BaseModel):
    """Preview of what would happen if execution is created."""
    skill_id: str
    skill_name: str
    execution_mode: str
    risk_level: str
    requires_approval: bool
    policy_decision: PolicyDecisionResponse
    targets_affected: list[str] = []
    estimated_duration_seconds: int = 0


class ApproveExecutionRequest(BaseModel):
    """Request to approve an execution."""
    approved_by: str = "operator"


class RejectExecutionRequest(BaseModel):
    """Request to reject an execution."""
    rejected_by: str = "operator"
    reason: str = ""


class ExecutionModeResponse(BaseModel):
    """Response for current execution mode status."""
    mode: str
    is_mock: bool
    is_integration: bool
    is_lab: bool
    should_execute_real: bool


# --- In-memory execution store (for demo/testing) ---
# In production, this would be persisted to the database

_executions: dict[str, dict] = {}


def _create_execution_record(
    skill_id: str,
    parameters: dict,
    status: str,
    risk: str,
    target_type: str | None = None,
    target_id: str | None = None,
    policy_decision: PolicyDecision | None = None,
) -> dict:
    """Create an execution record with mode and policy tracking."""
    now = datetime.now(timezone.utc).isoformat()
    skill = skill_registry.get(skill_id)
    current_mode = get_execution_mode()
    
    # Convert policy decision to dict if present
    policy_dict = policy_decision.to_dict() if policy_decision else None
    
    return {
        "id": str(uuid4()),
        "skill_id": skill_id,
        "skill_name": skill.meta.name if skill else skill_id,
        "status": status,
        "risk_level": risk,
        "parameters": parameters,
        "created_at": now,
        "updated_at": now,
        # Mode and policy tracking
        "execution_mode": current_mode.value,
        "policy_decision": policy_dict,
        # Target info
        "target_type": target_type,
        "target_id": target_id,
        # Approval tracking
        "approved_at": None,
        "approved_by": None,
        "rejected_at": None,
        "rejected_by": None,
        "rejection_reason": None,
        # Execution tracking
        "executed_at": None,
        "result": None,
        "error_message": None,
    }


def _infer_target_info(skill_id: str, parameters: dict) -> tuple[str, str]:
    """Infer target type and ID from skill and parameters."""
    # Try to determine target type from skill tags or ID
    target_type = "docker"  # Default
    if "proxmox" in skill_id or "vm" in skill_id or "lxc" in skill_id:
        target_type = "proxmox"
    
    # Try to get target ID from common parameter names
    target_id = (
        parameters.get("container_name") or
        parameters.get("container") or
        parameters.get("vmid") or
        parameters.get("target") or
        parameters.get("node") or
        ""
    )
    
    return target_type, target_id


# --- Endpoints ---

@router.get("/skills", response_model=SkillCatalogResponse)
async def list_skills(
    category: Optional[str] = Query(None, description="Filter by category"),
    risk: Optional[str] = Query(None, description="Filter by risk level"),
) -> SkillCatalogResponse:
    """List all available skills in the catalog."""
    all_skills = skill_registry.list_all()
    
    filtered = []
    for skill in all_skills:
        if category and skill.meta.category.value != category:
            continue
        if risk and skill.meta.risk.value != risk:
            continue
        filtered.append(SkillMetaResponse(
            id=skill.meta.id,
            name=skill.meta.name,
            description=skill.meta.description,
            category=skill.meta.category.value,
            risk=skill.meta.risk.value,
            target_types=skill.meta.target_types,
            required_params=skill.meta.required_params,
            optional_params=skill.meta.optional_params,
            estimated_duration_seconds=skill.meta.estimated_duration_seconds,
            tags=skill.meta.tags,
            requires_confirmation=skill.meta.requires_confirmation,
        ))
    
    categories = list(set(s.meta.category.value for s in all_skills))
    
    return SkillCatalogResponse(
        skills=filtered,
        categories=sorted(categories),
        total=len(filtered),
    )


@router.get("/mode", response_model=ExecutionModeResponse)
async def get_current_execution_mode() -> ExecutionModeResponse:
    """Get the current execution mode status."""
    current_mode = get_execution_mode()
    return ExecutionModeResponse(
        mode=current_mode.value,
        is_mock=is_mock_mode(),
        is_integration=is_integration_mode(),
        is_lab=is_lab_mode(),
        should_execute_real=not is_mock_mode(),
    )


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    status: Optional[str] = Query(None, description="Filter by status (pending_approval,approved,rejected,completed,failed,escalated)"),
    risk: Optional[str] = Query(None, description="Filter by risk level (low,medium,high)"),
    mode: Optional[str] = Query(None, description="Filter by execution mode (mock,integration,lab)"),
    skill_id: Optional[str] = Query(None, description="Filter by skill ID"),
    target: Optional[str] = Query(None, description="Search by target ID (container name, vm id)"),
    search: Optional[str] = Query(None, description="Search by execution ID, skill name, or target"),
    sort: Optional[str] = Query("newest", description="Sort order (newest, oldest_pending)"),
    needs_attention: bool = Query(False, description="Show only items needing attention"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ExecutionListResponse:
    """List skill executions with filtering and search."""
    all_execs = list(_executions.values())
    
    # Filter: needs_attention (pending_approval, escalated, failed)
    if needs_attention:
        attention_statuses = {"pending_approval", "escalated", "failed"}
        all_execs = [e for e in all_execs if e["status"] in attention_statuses]
    
    # Filter by status
    if status:
        status_list = [s.strip() for s in status.split(",")]
        all_execs = [e for e in all_execs if e["status"] in status_list]
    
    # Filter by risk
    if risk:
        risk_list = [r.strip() for r in risk.split(",")]
        all_execs = [e for e in all_execs if e.get("risk_level") in risk_list]
    
    # Filter by mode
    if mode:
        mode_list = [m.strip() for m in mode.split(",")]
        all_execs = [e for e in all_execs if e.get("execution_mode") in mode_list]
    
    # Filter by skill_id
    if skill_id:
        all_execs = [e for e in all_execs if e["skill_id"] == skill_id]
    
    # Filter by target
    if target:
        all_execs = [e for e in all_execs if target.lower() in (e.get("target_id") or "").lower()]
    
    # Search across multiple fields
    if search:
        search_lower = search.lower()
        all_execs = [
            e for e in all_execs
            if (
                search_lower in e["id"].lower() or
                search_lower in e["skill_id"].lower() or
                search_lower in e.get("skill_name", "").lower() or
                search_lower in (e.get("target_id") or "").lower()
            )
        ]
    
    # Sort
    if sort == "oldest_pending":
        # Put pending items first, then sort oldest first
        all_execs.sort(key=lambda x: (
            0 if x["status"] == "pending_approval" else 1,
            x["created_at"]
        ))
    else:  # newest
        all_execs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    total = len(all_execs)
    start = (page - 1) * page_size
    end = start + page_size
    page_execs = all_execs[start:end]
    
    return ExecutionListResponse(
        executions=[ExecutionResponse(**e) for e in page_execs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/preview", response_model=PreviewExecutionResponse)
async def preview_execution(request: PreviewExecutionRequest) -> PreviewExecutionResponse:
    """Preview what would happen if an execution is created.
    
    This is the 'dry run' step - shows mode, risk, policy decision before committing.
    """
    skill = skill_registry.get(request.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    
    # Infer target info if not provided
    target_type = request.target_type
    target_id = request.target_id
    if not target_type or not target_id:
        inferred_type, inferred_id = _infer_target_info(request.skill_id, request.parameters)
        target_type = target_type or inferred_type
        target_id = target_id or inferred_id
    
    # Get policy decision
    safety_policy = get_safety_policy()
    policy_decision = safety_policy.get_policy_decision(
        skill_id=request.skill_id,
        target_type=target_type,
        target_id=target_id,
        parameters=request.parameters,
    )
    
    # Determine if approval is required
    risk = skill.meta.risk.value
    requires_approval = risk != "low" or not policy_decision.allowed
    
    # Build targets affected list
    targets_affected = []
    if target_id:
        targets_affected.append(f"{target_type}://{target_id}")
    
    return PreviewExecutionResponse(
        skill_id=request.skill_id,
        skill_name=skill.meta.name,
        execution_mode=get_execution_mode().value,
        risk_level=risk,
        requires_approval=requires_approval,
        policy_decision=PolicyDecisionResponse(**policy_decision.to_dict()),
        targets_affected=targets_affected,
        estimated_duration_seconds=skill.meta.estimated_duration_seconds,
    )


@router.post("", response_model=ExecutionResponse)
async def create_execution(request: CreateExecutionRequest) -> ExecutionResponse:
    """Create a new skill execution request."""
    skill = skill_registry.get(request.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    
    # Infer target info if not provided
    target_type = request.target_type
    target_id = request.target_id
    if not target_type or not target_id:
        inferred_type, inferred_id = _infer_target_info(request.skill_id, request.parameters)
        target_type = target_type or inferred_type
        target_id = target_id or inferred_id
    
    # Get policy decision
    safety_policy = get_safety_policy()
    policy_decision = safety_policy.get_policy_decision(
        skill_id=request.skill_id,
        target_type=target_type,
        target_id=target_id,
        parameters=request.parameters,
    )
    
    # Determine initial status based on risk level, skip_approval flag, and policy
    risk = skill.meta.risk.value
    if not policy_decision.allowed:
        # Policy blocked - create in rejected state with reason
        status = SkillExecutionStatus.rejected.value
    elif request.skip_approval and risk == "low":
        status = SkillExecutionStatus.approved.value
    else:
        status = SkillExecutionStatus.pending_approval.value
    
    record = _create_execution_record(
        skill_id=request.skill_id,
        parameters=request.parameters,
        status=status,
        risk=risk,
        target_type=target_type,
        target_id=target_id,
        policy_decision=policy_decision,
    )
    
    # If policy blocked, set rejection info
    if not policy_decision.allowed:
        record["rejected_at"] = record["created_at"]
        record["rejected_by"] = "safety_policy"
        record["rejection_reason"] = policy_decision.primary_reason
    
    _executions[record["id"]] = record
    logger.info(f"[Executions] Created execution {record['id']} for skill {request.skill_id} (mode={record['execution_mode']}, status={status})")
    
    return ExecutionResponse(**record)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str) -> ExecutionResponse:
    """Get a specific execution by ID."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return ExecutionResponse(**_executions[execution_id])


@router.post("/{execution_id}/approve", response_model=ExecutionResponse)
async def approve_execution(
    execution_id: str, 
    request: ApproveExecutionRequest,
    user: Optional[User] = Depends(get_current_user),
) -> ExecutionResponse:
    """Approve a pending execution.
    
    When auth is enabled, requires appropriate permission based on risk level.
    The approving user is recorded for audit trail.
    """
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    record = _executions[execution_id]
    
    if record["status"] != SkillExecutionStatus.pending_approval.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve execution in status: {record['status']}"
        )
    
    # Check permission if auth enabled
    settings = get_settings()
    if settings.auth_enabled:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        risk = record.get("risk_level", "high")
        required_perm = get_approval_permission_for_risk(risk)
        if required_perm and not user.has_permission(required_perm):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission '{required_perm.value}' required to approve {risk}-risk executions"
            )
    
    now = datetime.now(timezone.utc).isoformat()
    record["status"] = SkillExecutionStatus.approved.value
    record["approved_at"] = now
    # Use authenticated user if available, otherwise fall back to request body
    record["approved_by"] = user.username if user else request.approved_by
    record["updated_at"] = now
    
    logger.info(f"[Executions] Approved execution {execution_id} by {record['approved_by']}")
    
    return ExecutionResponse(**record)


@router.post("/{execution_id}/reject", response_model=ExecutionResponse)
async def reject_execution(
    execution_id: str, 
    request: RejectExecutionRequest,
    user: Optional[User] = Depends(get_current_user),
) -> ExecutionResponse:
    """Reject a pending execution.
    
    When auth is enabled, requires appropriate permission based on risk level.
    The rejecting user is recorded for audit trail.
    """
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    record = _executions[execution_id]
    
    if record["status"] != SkillExecutionStatus.pending_approval.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject execution in status: {record['status']}"
        )
    
    # Check permission if auth enabled
    settings = get_settings()
    if settings.auth_enabled:
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not user.has_permission(Permission.REJECT_EXECUTION):
            raise HTTPException(
                status_code=403, 
                detail="Permission 'reject:execution' required"
            )
    
    now = datetime.now(timezone.utc).isoformat()
    record["status"] = SkillExecutionStatus.rejected.value
    record["rejected_at"] = now
    # Use authenticated user if available, otherwise fall back to request body
    record["rejected_by"] = user.username if user else request.rejected_by
    record["rejection_reason"] = request.reason
    record["updated_at"] = now
    
    logger.info(f"[Executions] Rejected execution {execution_id} by {record['rejected_by']}: {request.reason}")
    
    return ExecutionResponse(**record)


@router.post("/{execution_id}/execute", response_model=ExecutionResponse)
async def execute_skill(execution_id: str) -> ExecutionResponse:
    """Execute an approved skill."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    record = _executions[execution_id]
    
    if record["status"] != SkillExecutionStatus.approved.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute: status is {record['status']}, must be approved"
        )
    
    # Use stored target info or infer
    target_type = record.get("target_type") or "docker"
    target_id = record.get("target_id") or ""
    
    if not target_id:
        target_type, target_id = _infer_target_info(record["skill_id"], record["parameters"])
    
    # Re-check safety policy at execution time (mode may have changed)
    safety_policy = get_safety_policy()
    policy_decision = safety_policy.get_policy_decision(
        skill_id=record["skill_id"],
        target_type=target_type,
        target_id=target_id,
        parameters=record["parameters"],
    )
    
    # Update the stored policy decision
    record["policy_decision"] = policy_decision.to_dict()
    
    if not policy_decision.allowed:
        record["status"] = SkillExecutionStatus.rejected.value
        record["rejection_reason"] = policy_decision.primary_reason
        record["rejected_by"] = "safety_policy"
        record["rejected_at"] = datetime.now(timezone.utc).isoformat()
        record["updated_at"] = record["rejected_at"]
        logger.warning(f"[Executions] Safety policy blocked execution {execution_id}: {policy_decision.primary_reason}")
        return ExecutionResponse(**record)
    
    # Log any warnings
    for finding in policy_decision.warning_findings:
        logger.warning(f"[Executions] Safety warning for {execution_id}: {finding.message}")
    
    now = datetime.now(timezone.utc).isoformat()
    record["executed_at"] = now
    
    try:
        # Execute the skill using the skill runner
        result = await skill_runner.execute(
            skill_id=record["skill_id"],
            parameters=record["parameters"],
            skip_approval=True,  # Already approved via API
        )
        
        record["status"] = SkillExecutionStatus.completed.value
        record["result"] = {
            "success": result.success,
            "output": result.output,
            "duration_ms": result.duration_ms,
            "executed_in_mode": get_execution_mode().value,
            "policy_warnings": [f.to_dict() for f in policy_decision.warning_findings],
        }
        
        logger.info(f"[Executions] Executed {execution_id} successfully in mode={get_execution_mode().value}")
        
    except Exception as e:
        record["status"] = SkillExecutionStatus.failed.value
        record["error_message"] = str(e)
        logger.error(f"[Executions] Execution {execution_id} failed: {e}")
    
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    return ExecutionResponse(**record)
