"""Control Plane - The Brain of the Homelab Copilot.

This module implements the core state machine that drives the autonomous loop.
States: OBSERVE -> ASSESS -> PLAN -> VALIDATE -> TODO -> APPROVAL -> EXECUTE -> VERIFY -> RECORD
"""

import asyncio
from enum import Enum
from datetime import datetime, timedelta
import logging
import time

from sqlalchemy import select

from homelab.storage.database import async_session_maker
from homelab.storage.models import (
    Incident,
    IncidentStatus,
    ActionHistory,
    ActionStatus,
    IncidentNarrative,
    TodoStep,
)
from homelab.collectors import fact_collector, log_collector
from homelab.control_plane.incident_detector import incident_detector
from homelab.control_plane.planner import planner
from homelab.control_plane.plan_executor import plan_executor
from homelab.control_plane.plan_validator import plan_validator
from homelab.control_plane.plan_proposal import validate_plan_proposal
from homelab.notifications.router import notification_router
from homelab.rag.narrative_generator import narrative_generator
from homelab.policy.policy_engine import policy_engine
from homelab.llm.providers import EmbeddingBlockedError

# Setup logger
logger = logging.getLogger("control_plane")
logger.setLevel(logging.INFO)

class ControlPlaneState(str, Enum):
    """The explicit states of the Control Plane loop."""
    OBSERVE = "observe"     # Collect facts & logs from environment
    ASSESS = "assess"       # Analyze for incidents (Detection)
    PLAN = "plan"           # Generate remediation plans for new incidents
    VALIDATE = "validate"   # Check plan safety/correctness (Deterministic)
    TODO = "todo"           # Queue plans for approval
    APPROVAL = "approval"   # Wait for user permission (if needed)
    EXECUTE = "execute"     # Run approved steps via Router
    VERIFY = "verify"       # Check if action fixed the issue
    RECORD = "record"       # Archive result & generate narrative

class ControlPlane:
    """Orchestrates the autonomous remediation loop."""

    def __init__(self):
        self.current_state = ControlPlaneState.OBSERVE
        self.last_run = None
        self.last_summarization = None
        self.last_rag_error_log = None
    
    async def run_loop(self):
        """Execute one full iteration of the control plane loop."""
        start_time = time.time()
        print("=== Starting Control Plane Loop ===")
        
        async with async_session_maker() as db:
            try:
                # 1. OBSERVE
                await self._transition_to(ControlPlaneState.OBSERVE)
                # In Phase 1: Call collectors purely for observation
                fact_counts = await fact_collector.collect_all(db)
                print(f"[ControlPlane] Collected facts: {fact_counts}")
                
                log_counts = await log_collector.collect_all_container_logs(db, since_minutes=10)
                file_log_counts = await log_collector.collect_all_file_logs(db)
                total_logs = sum(log_counts.values()) + sum(file_log_counts.values())
                if total_logs > 0:
                    print(f"[ControlPlane] Collected {total_logs} new logs")
                
                # 2. ASSESS
                await self._transition_to(ControlPlaneState.ASSESS)
                # In Phase 1: Detect incidents
                new_incidents = await incident_detector.detect_all(db)
                if new_incidents:
                    print(f"[ControlPlane] Detected {len(new_incidents)} new incidents")
                
                # 3. PLAN
                await self._transition_to(ControlPlaneState.PLAN)
                # Fetch open incidents needing plans
                result = await db.execute(
                    select(Incident).where(Incident.status == IncidentStatus.open)
                )
                incidents_needing_plans = result.scalars().all()

                new_plans = []
                for incident in incidents_needing_plans:
                    existing_todos = await db.execute(
                        select(TodoStep)
                        .where(TodoStep.incident_id == incident.id)
                        .where(TodoStep.status.in_([ActionStatus.pending, ActionStatus.approved, ActionStatus.executing]))
                    )
                    if existing_todos.scalars().first():
                        continue

                    proposal = await planner.propose_for_incident(db, incident)
                    is_schema_valid, schema_errors = validate_plan_proposal(proposal)
                    if not is_schema_valid:
                        print(f"[ControlPlane] Plan rejected by schema validation: {schema_errors}")
                        continue
                    
                    # Policy Limit Check (Now Async)
                    is_valid, violations = await policy_engine.validate(db, proposal)
                    if not is_valid:
                        print(f"[ControlPlane] Plan rejected by policy: {violations}")
                        continue

                    for step in proposal.steps:
                        todo = TodoStep(
                            plan_id=proposal.id,
                            incident_id=incident.id,
                            order=step.order,
                            action_template=step.action,
                            target_resource=step.target,
                            parameters=step.params,
                            description=step.description,
                            verification=step.verification,
                            status=ActionStatus.pending,
                        )
                        db.add(todo)
                        new_plans.append(todo)

                if new_plans:
                    print(f"[ControlPlane] Proposed {len(new_plans)} new plans")

                
                # 4. VALIDATE
                await self._transition_to(ControlPlaneState.VALIDATE)
                
                # Fetch pending plans
                result = await db.execute(
                    select(TodoStep).where(TodoStep.status == ActionStatus.pending)
                )
                pending_plans = result.scalars().all()
                
                valid_plans = []
                for plan in pending_plans:
                    is_valid, reason = await plan_validator.validate_todo_step(db, plan)
                    if not is_valid:
                        print(f"[ControlPlane] Invalid Plan {plan.id}: {reason}")
                        plan.status = ActionStatus.failed
                        plan.error = reason
                    else:
                        valid_plans.append(plan)
                
                # 5. TODO
                await self._transition_to(ControlPlaneState.TODO)
                # Plans are already pending in DB effectively in TODO state
                if valid_plans:
                    print(f"[ControlPlane] {len(valid_plans)} plans awaiting approval")
                    await notification_router.notify_event(
                        "approval_required",
                        {
                            "pending_count": len(valid_plans),
                            "incident_ids": list({plan.incident_id for plan in valid_plans if plan.incident_id}),
                        },
                        severity="info",
                        tags=["approval"],
                    )
                
                # 6. APPROVAL
                await self._transition_to(ControlPlaneState.APPROVAL)
                # Fetch approved plans
                result = await db.execute(
                    select(TodoStep).where(TodoStep.status == ActionStatus.approved)
                )
                approved_plans = result.scalars().all()
                
                # 7. EXECUTE
                await self._transition_to(ControlPlaneState.EXECUTE)
                
                for plan in approved_plans:
                    # Run execution asynchronously to not block loop too long??
                    # For MVP, run sequentially
                    action = None
                    if plan.action_history_id:
                        result = await db.execute(
                            select(ActionHistory).where(ActionHistory.id == plan.action_history_id)
                        )
                        action = result.scalar_one_or_none()
                    if action is None:
                        action = ActionHistory(
                            incident_id=plan.incident_id,
                            action_template=plan.action_template,
                            target_resource=plan.target_resource,
                            parameters={
                                "params": plan.parameters,
                                "plan_id": plan.plan_id,
                                "description": plan.description,
                            },
                            status=ActionStatus.approved,
                            approved_at=plan.approved_at or datetime.utcnow(),
                        )
                        db.add(action)
                        await db.flush()
                        plan.action_history_id = action.id
                    print(f"[ControlPlane] Executing approved plan {plan.id}")
                    success = await plan_executor.execute_action(db, action.id)
                    plan.status = action.status
                    plan.executed_at = action.executed_at
                    plan.completed_at = action.completed_at
                    plan.result = action.result
                    plan.error = action.error
                    if success:
                        print(f"[ControlPlane] Plan {plan.id} executed successfully")
                    else:
                        print(f"[ControlPlane] Plan {plan.id} execution failed")
                
                # 8. VERIFY
                await self._transition_to(ControlPlaneState.VERIFY)
                
                # Check recent completed plans to see if they resolved the incident
                # Look for TodoSteps completed in the last 5 minutes
                five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
                result = await db.execute(
                    select(TodoStep)
                    .where(TodoStep.status == ActionStatus.completed)
                    .where(TodoStep.completed_at >= five_mins_ago)
                )
                recent_steps = result.scalars().all()
                
                for step in recent_steps:
                    if not step.incident_id:
                        continue
                        
                    # Re-collect facts for this target to confirm health
                    print(f"[ControlPlane] Verifying fix for {step.target_resource}")
                    try:
                        # Force fresh collection
                        # For now, we assume if action completed successfully, we mark incident as 'mitigated'
                        # In future: check specific facts (e.g. status=running)
                        
                        # Find the incident
                        incident_q = await db.execute(select(Incident).where(Incident.id == step.incident_id))
                        inc = incident_q.scalar_one_or_none()
                        
                        if inc and inc.status == IncidentStatus.open:
                            print(f"[ControlPlane] Marking incident {inc.id} as MITIGATED following successful action")
                            inc.status = IncidentStatus.mitigated
                            db.add(inc)
                    except Exception as e:
                        print(f"[ControlPlane] Verification failed: {e}")
                
                # 9. RECORD
                await self._transition_to(ControlPlaneState.RECORD)
                
                try:
                    # A. Summarize expiring logs (Long-term memory)
                    # Only run every hour to preserve resources
                    should_summarize = False
                    now = datetime.utcnow()
                    if not self.last_summarization or (now - self.last_summarization).total_seconds() > 3600:
                        should_summarize = True
                    
                    if should_summarize:
                        print("[ControlPlane] Running hourly log summarization and analysis...")
                        from homelab.rag.log_summarizer import log_summarizer
                        await log_summarizer.summarize_expiring_logs(db, retention_days=90)
                    
                        # B. Generate narratives for open incidents with placeholder narratives
                        
                        # Find incidents with placeholder narratives
                        result = await db.execute(
                            select(Incident)
                            .join(IncidentNarrative)
                            .where(IncidentNarrative.narrative_text.contains("Analysis pending..."))
                        )
                        incidents_needing_analysis = result.scalars().all()
                        
                        for incident in incidents_needing_analysis:
                            print(f"[ControlPlane] Generating analysis for incident {incident.id}")
                            await narrative_generator.generate_narrative(db, incident.id)
                            
                        self.last_summarization = now
                
                except EmbeddingBlockedError:
                    # Rate-limited logging for RAG blocks
                    now = datetime.utcnow()
                    if not self.last_rag_error_log or (now - self.last_rag_error_log).total_seconds() > 300: # 5 minutes
                        print(f"[ControlPlane] WARNING: RAG blocked due to consistent state. Background tasks paused.")
                        self.last_rag_error_log = now
                    # Else: suppress log spam
                
                await db.commit()
                
            except Exception as e:
                print(f"[ControlPlane] Error in Loop: {e}")
                import traceback
                traceback.print_exc()
                await db.rollback()
            finally:
                duration = time.time() - start_time
                self.last_run = datetime.utcnow()
                print(f"=== Control Plane Loop Completed in {duration:.2f}s ===\n")

    async def _transition_to(self, new_state: ControlPlaneState):
        """Log state transition."""
        # print(f"[State Transition] {self.current_state} -> {new_state}")
        self.current_state = new_state

# Singleton instance
control_plane = ControlPlane()
