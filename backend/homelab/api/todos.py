"""API for managing TodoSteps (Approvals)."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from homelab.storage.database import get_db
from homelab.storage.models import TodoStep, ActionStatus

router = APIRouter(prefix="/api/todos", tags=["todos"])

class TodoStepResponse(BaseModel):
    id: str
    incident_id: Optional[str]
    plan_id: Optional[str]
    order: int
    action_template: str
    target_resource: str
    parameters: dict
    description: Optional[str]
    verification: Optional[str]
    status: str
    created_at: datetime
    approved_at: Optional[datetime]
    executed_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[dict]
    error: Optional[str]

    class Config:
        from_attributes = True

@router.get("", response_model=List[TodoStepResponse])
async def list_todos(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List todo steps, optionally filtered by status."""
    query = select(TodoStep)
    if status is not None:
        try:
            status_enum = ActionStatus[status]
            query = query.where(TodoStep.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Default sort by created_at desc
    query = query.order_by(TodoStep.created_at.desc())
    
    result = await db.execute(query)
    todos = result.scalars().all()
    return todos

@router.post("/{todo_id}/approve")
async def approve_todo(
    todo_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending todo step for execution."""
    result = await db.execute(select(TodoStep).where(TodoStep.id == todo_id))
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(status_code=404, detail="Todo step not found")
        
    if todo.status != ActionStatus.pending:
        raise HTTPException(status_code=400, detail=f"Todo status is {todo.status}, cannot approve")
        
    todo.status = ActionStatus.approved
    todo.approved_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Todo step approved", "todo_id": todo_id}

@router.post("/{todo_id}/reject")
async def reject_todo(
    todo_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Reject a pending todo step."""
    result = await db.execute(select(TodoStep).where(TodoStep.id == todo_id))
    todo = result.scalar_one_or_none()
    
    if not todo:
        raise HTTPException(status_code=404, detail="Todo step not found")
        
    if todo.status != ActionStatus.pending:
        raise HTTPException(
            status_code=400, 
            detail=f"Todo status is {todo.status}, cannot reject"
        )
    
    todo.status = ActionStatus.failed
    todo.error = "User rejected step"
    await db.commit()
    
    return {"message": "Todo step rejected", "todo_id": todo_id}
