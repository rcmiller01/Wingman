"""Skills API - browse, run, and manage executable skills.

Endpoints:
- GET /api/skills - List all available skills
- GET /api/skills/{id} - Get skill details
- GET /api/skills/{id}/render - Render skill template with parameters
- POST /api/skills/suggest - Get skill suggestions for symptoms
- POST /api/skills/{id}/run - Create skill execution request
- POST /api/skills/executions/{id}/approve - Approve pending execution
- POST /api/skills/executions/{id}/execute - Execute approved skill
- GET /api/skills/executions - List executions
- GET /api/skills/executions/{id} - Get execution details
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from homelab.skills import (
    skill_registry,
    skill_runner,
    SkillCategory,
    SkillRisk,
    SkillExecutionStatus,
)
from homelab.skills.models import (
    SkillMetaResponse,
    SkillListResponse,
    SkillRunRequest,
    SkillExecutionResponse,
    SkillApprovalRequest,
    SkillSuggestionRequest,
    SkillSuggestionResponse,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ============================================================================
# Skill Registry Endpoints
# ============================================================================

@router.get("", response_model=SkillListResponse)
async def list_skills(
    category: str | None = Query(None, description="Filter by category"),
    risk: str | None = Query(None, description="Filter by risk level"),
    target_type: str | None = Query(None, description="Filter by target type (docker, proxmox)"),
    search: str | None = Query(None, description="Search in name, description, tags"),
):
    """List all available skills with optional filtering."""
    skills = skill_registry.list_all()
    
    # Apply filters
    if category:
        try:
            cat_enum = SkillCategory(category)
            skills = [s for s in skills if s.meta.category == cat_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    if risk:
        try:
            risk_enum = SkillRisk(risk)
            skills = [s for s in skills if s.meta.risk == risk_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk}")
    
    if target_type:
        skills = [s for s in skills if target_type in s.meta.target_types]
    
    if search:
        skills = skill_registry.search(search)
    
    # Convert to response models
    skill_responses = [
        SkillMetaResponse(
            id=s.meta.id,
            name=s.meta.name,
            description=s.meta.description,
            category=s.meta.category.value,
            risk=s.meta.risk.value,
            target_types=s.meta.target_types,
            required_params=s.meta.required_params,
            optional_params=s.meta.optional_params,
            estimated_duration_seconds=s.meta.estimated_duration_seconds,
            requires_confirmation=s.meta.requires_confirmation,
            tags=s.meta.tags,
        )
        for s in skills
    ]
    
    return SkillListResponse(skills=skill_responses, total=len(skill_responses))


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get detailed information about a specific skill."""
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    return {
        "id": skill.meta.id,
        "name": skill.meta.name,
        "description": skill.meta.description,
        "category": skill.meta.category.value,
        "risk": skill.meta.risk.value,
        "target_types": skill.meta.target_types,
        "required_params": skill.meta.required_params,
        "optional_params": skill.meta.optional_params,
        "estimated_duration_seconds": skill.meta.estimated_duration_seconds,
        "requires_confirmation": skill.meta.requires_confirmation,
        "tags": skill.meta.tags,
        "template": skill.template,
        "verification_template": skill.verification_template,
    }


class RenderRequest(BaseModel):
    """Request to render a skill template."""
    parameters: dict[str, Any]


@router.post("/{skill_id}/render")
async def render_skill(skill_id: str, request: RenderRequest):
    """Render a skill's template with provided parameters."""
    from jinja2 import Template
    
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    try:
        template = Template(skill.template)
        rendered = template.render(**request.parameters)
        
        verification_rendered = None
        if skill.verification_template:
            verification_template = Template(skill.verification_template)
            verification_rendered = verification_template.render(**request.parameters)
        
        return {
            "skill_id": skill_id,
            "rendered_command": rendered,
            "verification_command": verification_rendered,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template rendering error: {e}")


@router.post("/suggest", response_model=list[SkillSuggestionResponse])
async def suggest_skills(request: SkillSuggestionRequest):
    """Get skill suggestions based on symptoms."""
    suggestions = skill_registry.suggest_skills(
        symptoms=request.symptoms,
        target=request.target,
        max_results=request.max_results,
    )
    return suggestions


# ============================================================================
# Skill Execution Endpoints
# ============================================================================

@router.post("/{skill_id}/run", response_model=SkillExecutionResponse)
async def run_skill(skill_id: str, request: SkillRunRequest):
    """
    Create a new skill execution request.
    
    For low-risk skills with skip_approval=True, execution can proceed immediately.
    Medium and high-risk skills always require explicit approval.
    
    Returns an execution record with status indicating next steps.
    """
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    
    try:
        execution = await skill_runner.create_execution(
            skill_id=skill_id,
            target=request.target,
            parameters=request.parameters,
            incident_id=request.incident_id,
            skip_approval=request.skip_approval,
        )
        
        requires_approval = execution.status == SkillExecutionStatus.pending_approval
        
        if requires_approval:
            message = f"Skill requires approval before execution (risk={skill.meta.risk.value})"
        else:
            message = "Skill approved, ready for execution"
        
        return SkillExecutionResponse(
            execution_id=execution.id,
            skill_id=skill_id,
            target=request.target,
            status=execution.status.value,
            requires_approval=requires_approval,
            estimated_duration_seconds=skill.meta.estimated_duration_seconds,
            message=message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_id}/approve")
async def approve_execution(execution_id: str, request: SkillApprovalRequest):
    """Approve a pending skill execution."""
    try:
        execution = await skill_runner.approve(
            execution_id=execution_id,
            approved_by=request.approved_by,
            comment=request.comment,
        )
        
        return {
            "execution_id": execution.id,
            "status": execution.status.value,
            "approved_by": execution.approved_by,
            "approved_at": execution.approved_at.isoformat() if execution.approved_at else None,
            "message": "Execution approved, ready to execute",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_id}/execute")
async def execute_skill(execution_id: str):
    """
    Execute an approved skill.
    
    This triggers the actual execution and returns the result.
    For high-risk skills, the result includes judge audit information.
    """
    try:
        execution = await skill_runner.execute(execution_id)
        
        return {
            "execution_id": execution.id,
            "skill_id": execution.skill_id,
            "target": execution.target,
            "status": execution.status.value,
            "result": execution.result,
            "error": execution.error,
            "logs": execution.logs,
            "audit_result": execution.audit_result,
            "retry_count": execution.retry_count,
            "escalation_reason": execution.escalation_reason,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "action_history_id": execution.action_history_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/executions")
async def list_executions(
    status: str | None = Query(None, description="Filter by status"),
    skill_id: str | None = Query(None, description="Filter by skill ID"),
):
    """List skill executions with optional filtering."""
    status_enum = None
    if status:
        try:
            status_enum = SkillExecutionStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    executions = skill_runner.list_executions(status=status_enum, skill_id=skill_id)
    
    return {
        "executions": [
            {
                "execution_id": e.id,
                "skill_id": e.skill_id,
                "target": e.target,
                "status": e.status.value,
                "created_at": e.created_at.isoformat(),
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "error": e.error,
                "retry_count": e.retry_count,
                "escalation_reason": e.escalation_reason,
            }
            for e in executions
        ],
        "total": len(executions),
    }


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get detailed information about a skill execution."""
    execution = skill_runner.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    skill = skill_registry.get(execution.skill_id)
    
    return {
        "execution_id": execution.id,
        "skill_id": execution.skill_id,
        "skill_name": skill.meta.name if skill else None,
        "target": execution.target,
        "parameters": execution.parameters,
        "status": execution.status.value,
        "created_at": execution.created_at.isoformat(),
        "approved_at": execution.approved_at.isoformat() if execution.approved_at else None,
        "approved_by": execution.approved_by,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "logs": execution.logs,
        "result": execution.result,
        "error": execution.error,
        "audit_result": execution.audit_result,
        "retry_count": execution.retry_count,
        "escalation_reason": execution.escalation_reason,
        "incident_id": execution.incident_id,
        "action_history_id": execution.action_history_id,
    }
