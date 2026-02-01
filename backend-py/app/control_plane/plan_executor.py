"""Plan Executor - executes approved plans step by step."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.plan_proposal import PlanProposal, PlanStep, PlanStatus, ActionType
from app.adapters import docker_adapter, proxmox_adapter
from app.storage.models import ActionHistory


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
        """Execute a single step and record in action history."""
        step.status = "executing"
        step.executed_at = datetime.utcnow()
        
        try:
            # Execute based on action type
            if step.action == ActionType.restart_container:
                success = await self._restart_container(step)
            elif step.action == ActionType.start_container:
                success = await self._start_container(step)
            elif step.action == ActionType.stop_container:
                success = await self._stop_container(step)
            else:
                step.result = {"message": f"Action {step.action} not implemented"}
                step.status = "failed"
                return False
            
            # Record action in history
            await self._record_action(
                db,
                plan_id=plan.id,
                incident_id=plan.incident_id,
                action=step.action.value,
                target=step.target,
                success=success,
                result=step.result,
            )
            
            step.status = "completed" if success else "failed"
            return success
            
        except Exception as e:
            step.status = "failed"
            step.result = {"error": str(e)}
            return False
    
    async def _restart_container(self, step: PlanStep) -> bool:
        """Restart a Docker container."""
        # Extract container ID from resource_ref (docker://container_id)
        container_id = step.target.replace("docker://", "")
        
        success = await docker_adapter.restart_container(
            container_id,
            timeout=step.params.get("timeout", 10),
        )
        
        step.result = {
            "message": f"Container {container_id} restarted" if success else "Restart failed",
            "success": success,
        }
        return success
    
    async def _start_container(self, step: PlanStep) -> bool:
        """Start a Docker container."""
        container_id = step.target.replace("docker://", "")
        
        success = await docker_adapter.start_container(container_id)
        
        step.result = {
            "message": f"Container {container_id} started" if success else "Start failed",
            "success": success,
        }
        return success
    
    async def _stop_container(self, step: PlanStep) -> bool:
        """Stop a Docker container."""
        container_id = step.target.replace("docker://", "")
        
        success = await docker_adapter.stop_container(
            container_id,
            timeout=step.params.get("timeout", 10),
        )
        
        step.result = {
            "message": f"Container {container_id} stopped" if success else "Stop failed",
            "success": success,
        }
        return success
    
    async def _record_action(
        self,
        db: AsyncSession,
        plan_id: str,
        incident_id: str | None,
        action: str,
        target: str,
        success: bool,
        result: dict | None,
    ):
        """Record action in action history."""
        history = ActionHistory(
            plan_id=plan_id,
            incident_id=incident_id,
            action=action,
            target=target,
            approved_by="user",  # In guide mode, always user approved
            executed_at=datetime.utcnow(),
            success=success,
            result=result,
        )
        db.add(history)


# Singleton
plan_executor = PlanExecutor()
