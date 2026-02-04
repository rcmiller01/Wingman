"""Executions API - skill execution management and lifecycle."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from homelab.skills import (
    skill_registry,
    skill_runner,
    execution_mode_manager,
    ExecutionMode,
    SkillCategory,
    SkillRisk,
    SkillExecutionStatus,
)

router = APIRouter(prefix="/api/executions", tags=["executions"])
logger = logging.getLogger(__name__)


# --- Response Models ---

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
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[str] = None
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    executed_at: Optional[str] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None


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
    skip_approval: bool = False  # Only works for low-risk skills


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


def _create_execution_record(skill_id: str, parameters: dict, status: str, risk: str) -> dict:
    """Create an execution record."""
    now = datetime.now(timezone.utc).isoformat()
    skill = skill_registry.get(skill_id)
    return {
        "id": str(uuid4()),
        "skill_id": skill_id,
        "skill_name": skill.meta.name if skill else skill_id,
        "status": status,
        "risk_level": risk,
        "parameters": parameters,
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "approved_by": None,
        "rejected_at": None,
        "rejected_by": None,
        "rejection_reason": None,
        "executed_at": None,
        "result": None,
        "error_message": None,
    }


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
async def get_execution_mode() -> ExecutionModeResponse:
    """Get the current execution mode status."""
    return ExecutionModeResponse(
        mode=execution_mode_manager.get_mode().value,
        is_mock=execution_mode_manager.is_mock(),
        is_integration=execution_mode_manager.is_integration(),
        is_lab=execution_mode_manager.is_lab(),
        should_execute_real=execution_mode_manager.should_execute_real(),
    )


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    status: Optional[str] = Query(None, description="Filter by status (pending_approval,approved,rejected,completed,failed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ExecutionListResponse:
    """List skill executions with optional filtering."""
    all_execs = list(_executions.values())
    
    # Filter by status
    if status:
        status_list = [s.strip() for s in status.split(",")]
        all_execs = [e for e in all_execs if e["status"] in status_list]
    
    # Sort by created_at descending (newest first)
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


@router.post("", response_model=ExecutionResponse)
async def create_execution(request: CreateExecutionRequest) -> ExecutionResponse:
    """Create a new skill execution request."""
    skill = skill_registry.get(request.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    
    # Determine initial status based on risk level and skip_approval flag
    risk = skill.meta.risk.value
    if request.skip_approval and risk == "low":
        status = SkillExecutionStatus.approved.value
    else:
        status = SkillExecutionStatus.pending_approval.value
    
    record = _create_execution_record(
        skill_id=request.skill_id,
        parameters=request.parameters,
        status=status,
        risk=risk,
    )
    
    _executions[record["id"]] = record
    logger.info(f"[Executions] Created execution {record['id']} for skill {request.skill_id}")
    
    return ExecutionResponse(**record)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str) -> ExecutionResponse:
    """Get a specific execution by ID."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    return ExecutionResponse(**_executions[execution_id])


@router.post("/{execution_id}/approve", response_model=ExecutionResponse)
async def approve_execution(execution_id: str, request: ApproveExecutionRequest) -> ExecutionResponse:
    """Approve a pending execution."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    record = _executions[execution_id]
    
    if record["status"] != SkillExecutionStatus.pending_approval.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve execution in status: {record['status']}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    record["status"] = SkillExecutionStatus.approved.value
    record["approved_at"] = now
    record["approved_by"] = request.approved_by
    record["updated_at"] = now
    
    logger.info(f"[Executions] Approved execution {execution_id} by {request.approved_by}")
    
    return ExecutionResponse(**record)


@router.post("/{execution_id}/reject", response_model=ExecutionResponse)
async def reject_execution(execution_id: str, request: RejectExecutionRequest) -> ExecutionResponse:
    """Reject a pending execution."""
    if execution_id not in _executions:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    record = _executions[execution_id]
    
    if record["status"] != SkillExecutionStatus.pending_approval.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject execution in status: {record['status']}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    record["status"] = SkillExecutionStatus.rejected.value
    record["rejected_at"] = now
    record["rejected_by"] = request.rejected_by
    record["rejection_reason"] = request.reason
    record["updated_at"] = now
    
    logger.info(f"[Executions] Rejected execution {execution_id} by {request.rejected_by}: {request.reason}")
    
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
        }
        
        logger.info(f"[Executions] Executed {execution_id} successfully")
        
    except Exception as e:
        record["status"] = SkillExecutionStatus.failed.value
        record["error_message"] = str(e)
        logger.error(f"[Executions] Execution {execution_id} failed: {e}")
    
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    return ExecutionResponse(**record)
