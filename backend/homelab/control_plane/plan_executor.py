"""Plan Executor - executes approved plans step by step."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.control_plane.plan_proposal import PlanProposal, PlanStep, PlanStatus, ActionType
from homelab.adapters import docker_adapter, proxmox_adapter
from homelab.storage.models import ActionHistory, ActionStatus, ActionTemplate
from homelab.notifications.webhook import notifier


class PlanExecutor:
    """Executes approved plan steps."""
    
    async def execute_plan(
        self,
        db: AsyncSession,
        plan: PlanProposal,
    ) -> PlanProposal:
        """Execute all steps in an approved plan."""
        if plan.status != PlanStatus.approved:
            plan.error = "Plan must be approved before execution"
            plan.status = PlanStatus.failed
            return plan
        
        plan.status = PlanStatus.executing
        plan.executed_at = datetime.utcnow()
        
        try:
            for step in plan.steps:
                success = await self._execute_step(db, plan, step)
                if not success:
                    plan.status = PlanStatus.failed
                    plan.error = f"Step {step.order} failed"
                    return plan
            
            plan.status = PlanStatus.completed
            plan.completed_at = datetime.utcnow()
            
        except Exception as e:
            plan.status = PlanStatus.failed
            plan.error = str(e)
        
        # Trigger notification
        import asyncio
        asyncio.create_task(notifier.notify("plan.status_changed", {
            "plan_id": plan.id,
            "status": plan.status.value,
            "incident_id": plan.incident_id,
            "error": plan.error
        }))
        
        return plan
    
    async def execute_single_step(
        self,
        db: AsyncSession,
        plan: PlanProposal,
        step_order: int,
    ) -> tuple[bool, str]:
        """Execute a single step (for step-by-step approval)."""
        # Find the step
        step = next((s for s in plan.steps if s.order == step_order), None)
        if not step:
            return False, f"Step {step_order} not found"
        
        # Check previous steps are complete
        for prev_step in plan.steps:
            if prev_step.order < step_order and prev_step.status != "completed":
                return False, f"Previous step {prev_step.order} not completed"
        
        success = await self._execute_step(db, plan, step)
        return success, step.result.get("message", "") if step.result else ""
    
    async def _execute_step(
        self,
        db: AsyncSession,
        plan: PlanProposal,
        step: PlanStep,
    ) -> bool:
        """Execute a single step via the Executor Router."""
        step.status = "executing"
        step.executed_at = datetime.utcnow()
        
        try:
            from homelab.control_plane.executor_router import executor_router
            
            # Delegate to executor router
            result = await executor_router.execute_step(step)
            
            step.result = result
            success = result.get("success", False)
            
            # Record action in history
            await self._record_action(
                db,
                incident_id=plan.incident_id,
                action=step.action.value,
                target=step.target,
                success=success,
                result=result,
            )
            
            step.status = "completed" if success else "failed"
            return success
            
        except Exception as e:
            step.status = "failed"
            step.result = {"error": str(e)}
            return False
    
    async def _record_action(
        self,
        db: AsyncSession,
        incident_id: str | None,
        action: str,
        target: str,
        success: bool,
        result: dict | None,
    ):
        """Record action in action history."""
        # Map raw action string to ActionTemplate if possible
        try:
            template = ActionTemplate(action)
        except ValueError:
            template = ActionTemplate.restart_resource # Fallback
            
        history = ActionHistory(
            incident_id=incident_id,
            action_template=template,
            target_resource=target,
            status=ActionStatus.completed if success else ActionStatus.failed,
            executed_at=datetime.utcnow(),
            result=result,
        )
        db.add(history)


# Singleton
plan_executor = PlanExecutor()
