"""Plans API endpoints for Guide Mode."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.storage import get_db
from app.storage.models import Incident
from app.control_plane import (
    plan_generator,
    plan_executor,
    PlanProposal,
    PlanStatus,
)
from app.policy import policy_engine


router = APIRouter(prefix="/api/plans", tags=["plans"])

# In-memory plan storage (for MVP - would be DB in production)
_plans: dict[str, PlanProposal] = {}


class CreatePlanRequest(BaseModel):
    """Request to create a manual plan."""
    title: str
    description: str
    steps: list[dict]
    incident_id: str | None = None


class ApproveStepRequest(BaseModel):
    """Request to approve a specific step."""
    step_order: int


@router.get("")
async def list_plans():
    """List all plans."""
    return {
        "count": len(_plans),
        "plans": [p.to_dict() for p in _plans.values()],
    }


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific plan."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    return plan.to_dict()


@router.post("/generate/{incident_id}")
async def generate_plan(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate a remediation plan for an incident."""
    # Get incident
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalars().first()
    
    if not incident:
        raise HTTPException(404, "Incident not found")
    
    # Generate plan
    plan = await plan_generator.generate_for_incident(db, incident)
    
    # Validate plan
    is_valid, violations = policy_engine.validate(plan)
    if not is_valid:
        return {
            "error": "Plan validation failed",
            "violations": violations,
        }
    
    # Store plan
    _plans[plan.id] = plan
    
    return {
        "plan": plan.to_dict(),
        "dangerous_steps": [s.order for s in policy_engine.check_dangerous(plan)],
    }


@router.post("/create")
async def create_plan(
    request: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a manual plan."""
    plan = plan_generator.create_manual_plan(
        title=request.title,
        description=request.description,
        steps=request.steps,
        incident_id=request.incident_id,
    )
    
    # Validate
    is_valid, violations = policy_engine.validate(plan)
    if not is_valid:
        raise HTTPException(400, {"error": "Validation failed", "violations": violations})
    
    _plans[plan.id] = plan
    
    return {
        "plan": plan.to_dict(),
        "dangerous_steps": [s.order for s in policy_engine.check_dangerous(plan)],
    }


@router.post("/{plan_id}/approve")
async def approve_plan(plan_id: str):
    """Approve an entire plan for execution."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    if plan.status != PlanStatus.pending:
        raise HTTPException(400, f"Plan is not pending (status: {plan.status.value})")
    
    plan.status = PlanStatus.approved
    plan.approved_by = "user"
    plan.approved_at = datetime.utcnow()
    
    return {
        "plan_id": plan_id,
        "status": "approved",
        "message": "Plan approved - use /execute to run",
    }


@router.post("/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Execute an approved plan."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    if plan.status != PlanStatus.approved:
        raise HTTPException(400, f"Plan must be approved first (status: {plan.status.value})")
    
    # Execute
    updated_plan = await plan_executor.execute_plan(db, plan)
    await db.commit()
    
    return {
        "plan": updated_plan.to_dict(),
        "success": updated_plan.status == PlanStatus.completed,
    }


@router.post("/{plan_id}/step")
async def execute_step(
    plan_id: str,
    request: ApproveStepRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a single step (step-by-step approval mode)."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    # Mark plan as approved if first step
    if plan.status == PlanStatus.pending:
        plan.status = PlanStatus.approved
        plan.approved_by = "user"
        plan.approved_at = datetime.utcnow()
    
    # Execute single step
    success, message = await plan_executor.execute_single_step(
        db, plan, request.step_order
    )
    await db.commit()
    
    # Check if all steps complete
    all_complete = all(s.status == "completed" for s in plan.steps)
    if all_complete:
        plan.status = PlanStatus.completed
        plan.completed_at = datetime.utcnow()
    
    return {
        "plan_id": plan_id,
        "step": request.step_order,
        "success": success,
        "message": message,
        "plan_status": plan.status.value,
        "all_complete": all_complete,
    }


@router.post("/{plan_id}/reject")
async def reject_plan(plan_id: str):
    """Reject a pending plan."""
    plan = _plans.get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    
    if plan.status != PlanStatus.pending:
        raise HTTPException(400, f"Can only reject pending plans (status: {plan.status.value})")
    
    plan.status = PlanStatus.rejected
    
    return {
        "plan_id": plan_id,
        "status": "rejected",
    }
