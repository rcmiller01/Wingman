"""API for managing remediation plans."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.database import get_db
from homelab.storage.models import ActionHistory, ActionStatus

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanResponse(BaseModel):
    id: str
    incident_id: str | None
    action_template: str
    target_resource: str
    parameters: dict
    status: str
    requested_at: datetime
    approved_at: datetime | None
    executed_at: datetime | None
    completed_at: datetime | None
    result: dict | None
    error: str | None

    class Config:
        from_attributes = True


@router.get("")
async def list_plans(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List action plans, optionally filtered by status."""
    query = select(ActionHistory)
    if status:
        try:
            status_enum = ActionStatus[status]
            query = query.where(ActionHistory.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(ActionHistory.requested_at.desc()).limit(50)
    result = await db.execute(query)
    plans = result.scalars().all()
    return {
        "count": len(plans),
        "plans": [PlanResponse.model_validate(plan) for plan in plans],
    }

@router.post("/{plan_id}/approve")
async def approve_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending plan for execution."""
    result = await db.execute(select(ActionHistory).where(ActionHistory.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if plan.status != ActionStatus.pending:
        raise HTTPException(status_code=400, detail=f"Plan status is {plan.status}, cannot approve")
        
    plan.status = ActionStatus.approved
    plan.approved_at = datetime.utcnow()
    await db.commit()
    return {"message": "Plan approved", "plan_id": plan_id}

@router.post("/{plan_id}/reject")
async def reject_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Reject (delete) a pending plan."""
    result = await db.execute(select(ActionHistory).where(ActionHistory.id == plan_id))
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    # We can either mark as rejected or delete. For MVP, failed/rejected is similar.
    plan.status = ActionStatus.failed
    plan.error = "User rejected plan"
    await db.commit()
    return {"message": "Plan rejected", "plan_id": plan_id}
