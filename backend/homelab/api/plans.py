"""API for managing remediation plans."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.database import get_db
from homelab.storage.models import ActionHistory, ActionStatus

router = APIRouter(prefix="/plans", tags=["plans"])

@router.get("/")
async def list_plans(
    status: ActionStatus | None = None,
    db: AsyncSession = Depends(get_db)
):
    """List action plans, optionally filtered by status."""
    query = select(ActionHistory)
    if status:
        query = query.where(ActionHistory.status == status)
    
    query = query.order_by(ActionHistory.requested_at.desc()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()

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
