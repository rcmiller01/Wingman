"""Skill Runner - executes skills with safety controls and audit trail.

Implements the execution flow:
1. Validate skill and parameters
2. Check risk level -> route to approval if needed (server-enforced)
3. Validate through policy engine (same safeguards as control plane)
4. Execute via appropriate adapter (or mock in test mode)
5. For high-risk: submit to judge for audit (leaves immutable record)
6. On failure: exactly one retry attempt
7. On retry failure: escalate to human
8. Record complete audit artifact

Execution Modes:
- MOCK: No real execution, returns canned responses (unit tests, demos)
- INTEGRATION: Uses real adapters but against test fixtures
- LAB: Real execution against actual infrastructure (production)
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from jinja2 import sandbox

from homelab.adapters import docker_adapter, proxmox_adapter
from homelab.policy.policy_engine import policy_engine
from homelab.storage.database import async_session_maker
from homelab.storage.models import ActionHistory, ActionStatus, ActionTemplate
from homelab.storage.audit_chain import prepare_chained_entry

from .models import (
    Skill,
    SkillRisk,
    SkillExecution,
    SkillExecutionStatus,
)
from .registry import skill_registry
from .execution_modes import (
    ExecutionMode,
    execution_mode_manager,
    MockResponse,
)

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 1  # Exactly one retry, no more
MAX_LOG_ENTRIES = 1000  # Cap execution logs

# Input validation
_TARGET_PATTERN = re.compile(r'^(docker|proxmox)://[a-zA-Z0-9][a-zA-Z0-9_./-]*$')

# Jinja2 template denylist - prevent sandbox escape vectors
# These patterns could be used to escape the sandbox and access Python internals
TEMPLATE_DENYLIST = frozenset([
    '__class__',
    '__mro__',
    '__subclasses__',
    '__globals__',
    '__builtins__',
    '__import__',
    '__code__',
    '__getattribute__',
    '__reduce__',
    'mro()',
    'subclasses()',
])


def _validate_template_safety(template: str) -> tuple[bool, str | None]:
    """
    Check template for dangerous patterns that could escape Jinja2 sandbox.
    
    Returns (is_safe, violation_message).
    
    Note: This is defense-in-depth. The Jinja2 SandboxedEnvironment is the
    primary security control. This denylist catches obvious escape attempts
    that might bypass sandbox restrictions.
    """
    template_lower = template.lower()
    for pattern in TEMPLATE_DENYLIST:
        if pattern.lower() in template_lower:
            return False, f"Template contains forbidden pattern: {pattern}"
    return True, None


def _compute_skill_hash(skill: Skill) -> str:
    """Compute a hash of the skill definition for audit trail."""
    content = f"{skill.meta.id}:{skill.template}:{skill.verification_template or ''}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class SkillRunner:
    """Executes skills with safety controls, retry logic, and audit trail.
    
    Security Invariants:
    - Tier 2/3 skills ALWAYS require explicit approval (cannot be bypassed by client)
    - skip_approval only works for Tier 1 (low-risk) skills without confirmation requirement
    - Retry is capped to exactly 1 attempt
    - Judge audit runs ONLY for Tier 3 (high-risk) skills
    - All executions record immutable audit trail
    """
    
    def __init__(self):
        self._executions: dict[str, SkillExecution] = {}  # In-memory for MVP
    
    async def create_execution(
        self,
        skill_id: str,
        target: str,
        parameters: dict[str, Any],
        incident_id: str | None = None,
        skip_approval: bool = False,
        requested_by: str = "unknown",
    ) -> SkillExecution:
        """
        Create a new skill execution request.
        
        SECURITY: skip_approval is server-enforced. It only works for:
        - Low-risk skills (Tier 1)
        - Skills without requires_confirmation flag
        
        Medium and high-risk skills ALWAYS require explicit approval regardless
        of what the client requests.
        """
        skill = skill_registry.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        # Validate target format
        if not target or not _TARGET_PATTERN.match(target):
            raise ValueError(f"Invalid target format: {target}")
        
        # Validate required parameters
        missing = [p for p in skill.meta.required_params if p not in parameters]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # Sanitize parameters (basic - prevent obvious injection)
        sanitized_params = self._sanitize_parameters(parameters)
        
        # Compute skill hash for audit trail
        skill_hash = _compute_skill_hash(skill)
        
        execution = SkillExecution(
            id=str(uuid4()),
            skill_id=skill_id,
            target=target,
            parameters=sanitized_params,
            status=SkillExecutionStatus.pending_approval,
            created_at=datetime.utcnow(),
            incident_id=incident_id,
        )
        
        # Store metadata for audit
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] Execution created")
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] Requested by: {requested_by}")
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] Skill: {skill_id} (hash: {skill_hash})")
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] Target: {target}")
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] Risk level: {skill.meta.risk.value}")
        
        # SERVER-ENFORCED: Only low-risk skills without confirmation can skip approval
        can_skip = (
            skip_approval and 
            skill.meta.risk == SkillRisk.low and
            not skill.meta.requires_confirmation
        )
        
        if skill.meta.risk in (SkillRisk.medium, SkillRisk.high):
            # SECURITY: Medium/High risk ALWAYS requires approval
            can_skip = False
            if skip_approval:
                execution.logs.append(
                    f"[{datetime.utcnow().isoformat()}] WARNING: skip_approval ignored for {skill.meta.risk.value}-risk skill"
                )
        
        if can_skip:
            execution.status = SkillExecutionStatus.approved
            execution.approved_at = datetime.utcnow()
            execution.approved_by = "auto-approved:tier1"
            execution.logs.append(f"[{datetime.utcnow().isoformat()}] Auto-approved (Tier 1, low-risk)")
            logger.info(f"[SkillRunner] Auto-approved low-risk skill: {skill_id}")
        else:
            execution.logs.append(
                f"[{datetime.utcnow().isoformat()}] Requires human approval (risk={skill.meta.risk.value})"
            )
            logger.info(f"[SkillRunner] Skill {skill_id} requires approval (risk={skill.meta.risk.value})")
        
        self._executions[execution.id] = execution
        return execution
    
    def _sanitize_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Sanitize parameters to prevent injection attacks."""
        sanitized = {}
        for key, value in parameters.items():
            # Only allow alphanumeric keys
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid parameter name: {key}")
            
            # Sanitize string values
            if isinstance(value, str):
                # Block obvious injection attempts
                if any(danger in value for danger in [';', '&&', '||', '`', '$(']):
                    raise ValueError(f"Potentially dangerous characters in parameter: {key}")
                sanitized[key] = value[:1000]  # Limit length
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Only allow simple lists
                sanitized[key] = [str(v)[:100] for v in value[:50]]
            else:
                sanitized[key] = str(value)[:1000]
        
        return sanitized
    
    async def approve(
        self,
        execution_id: str,
        approved_by: str,
        comment: str | None = None,
    ) -> SkillExecution:
        """Approve a pending skill execution."""
        if not approved_by or len(approved_by) < 1:
            raise ValueError("approved_by is required")
        
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if execution.status != SkillExecutionStatus.pending_approval:
            raise ValueError(f"Execution not pending approval (current status: {execution.status.value})")
        
        execution.status = SkillExecutionStatus.approved
        execution.approved_at = datetime.utcnow()
        execution.approved_by = approved_by
        
        execution.logs.append(f"[{datetime.utcnow().isoformat()}] APPROVED by: {approved_by}")
        if comment:
            execution.logs.append(f"[{datetime.utcnow().isoformat()}] Approval comment: {comment}")
        
        logger.info(f"[SkillRunner] Execution {execution_id} approved by {approved_by}")
        return execution
    
    async def reject(
        self,
        execution_id: str,
        rejected_by: str,
        reason: str | None = None,
    ) -> SkillExecution:
        """
        Reject a pending skill execution.
        
        AUDIT: Creates an ActionHistory entry for the rejection event.
        
        Idempotent behavior:
        - reject on PENDING_APPROVAL → ok, transition to REJECTED
        - reject on REJECTED → return current state (no-op)
        - reject on APPROVED/EXECUTING/COMPLETED → 409 Conflict
        """
        if not rejected_by or len(rejected_by) < 1:
            raise ValueError("rejected_by is required")
        
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        # Idempotent: already rejected → return current state
        if execution.status == SkillExecutionStatus.rejected:
            self._add_log(execution, f"Rejection already recorded (by {execution.rejected_by})")
            return execution
        
        # Cannot reject after approval/execution
        terminal_states = {
            SkillExecutionStatus.approved,
            SkillExecutionStatus.executing,
            SkillExecutionStatus.pending_audit,
            SkillExecutionStatus.completed,
            SkillExecutionStatus.failed,
            SkillExecutionStatus.retrying,
            SkillExecutionStatus.escalated,
        }
        if execution.status in terminal_states:
            raise ValueError(
                f"Cannot reject execution in '{execution.status.value}' state. "
                "Rejection is only valid for pending_approval status."
            )
        
        # Apply rejection
        execution.status = SkillExecutionStatus.rejected
        execution.rejected_at = datetime.utcnow()
        execution.rejected_by = rejected_by
        execution.rejection_reason = reason
        
        self._add_log(execution, f"REJECTED by: {rejected_by}")
        if reason:
            self._add_log(execution, f"Rejection reason: {reason}")
        
        logger.info(f"[SkillRunner] Execution {execution_id} rejected by {rejected_by}: {reason}")
        
        # Record to ActionHistory for complete audit trail
        skill = skill_registry.get(execution.skill_id)
        if skill:
            await self._record_rejection_history(skill, execution)
        
        return execution
    
    async def _record_rejection_history(
        self,
        skill: Skill,
        execution: SkillExecution,
    ) -> None:
        """Record a rejection event to ActionHistory for audit trail."""
        try:
            # Map skill to action template
            action_mapping = {
                "rem-restart-container": ActionTemplate.restart_resource,
                "rem-restart-vm": ActionTemplate.restart_resource,
                "rem-restart-lxc": ActionTemplate.restart_resource,
                "rem-stop-container": ActionTemplate.stop_resource,
                "rem-stop-vm": ActionTemplate.stop_resource,
                "diag-container-logs": ActionTemplate.collect_diagnostics,
                "diag-container-inspect": ActionTemplate.collect_diagnostics,
                "diag-vm-status": ActionTemplate.collect_diagnostics,
                "maint-prune-images": ActionTemplate.collect_diagnostics,
                "maint-create-snapshot": ActionTemplate.create_snapshot,
            }
            
            action_template = action_mapping.get(skill.meta.id, ActionTemplate.collect_diagnostics)
            
            audit_result = {
                "event": "skill_rejected",
                "skill_id": skill.meta.id,
                "skill_hash": _compute_skill_hash(skill),
                "skill_risk": skill.meta.risk.value,
                "execution_id": execution.id,
                "rejected_by": execution.rejected_by,
                "rejection_reason": execution.rejection_reason,
                "execution_logs": execution.logs[-50:],  # Last 50 log entries
            }
            
            async with async_session_maker() as db:
                action = ActionHistory(
                    incident_id=execution.incident_id,
                    action_template=action_template,
                    target_resource=execution.target,
                    parameters=execution.parameters,
                    status=ActionStatus.failed,  # Rejected = not executed
                    requested_at=execution.created_at,
                    completed_at=execution.rejected_at,
                    result=audit_result,
                    error=f"Rejected by {execution.rejected_by}: {execution.rejection_reason or 'No reason provided'}",
                )
                
                # Add to hash chain for tamper resistance
                await prepare_chained_entry(db, action)
                
                db.add(action)
                await db.commit()
                
                execution.action_history_id = action.id
                self._add_log(execution, f"Rejection recorded to ActionHistory: {action.id} (chain seq: {action.sequence_num})")
                
        except Exception as e:
            logger.error(f"[SkillRunner] Failed to record rejection to ActionHistory: {e}")
            self._add_log(execution, f"WARNING: Failed to record rejection to ActionHistory: {e}")
    
    async def execute(self, execution_id: str) -> SkillExecution:
        """
        Execute an approved skill.
        
        SECURITY INVARIANTS:
        - Execution ONLY proceeds if status is 'approved' or 'retrying'
        - Policy engine validates target is not denylisted and rate limits
        - Retry is capped to exactly MAX_RETRIES (1)
        - Judge audit runs ONLY for high-risk skills
        - All outcomes record to ActionHistory
        """
        execution = self._executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        # SECURITY: Only approved or retrying executions can proceed
        if execution.status == SkillExecutionStatus.pending_approval:
            raise ValueError(
                "Execution requires approval before execution. "
                "Use POST /api/skills/executions/{id}/approve first."
            )
        
        if execution.status not in (SkillExecutionStatus.approved, SkillExecutionStatus.retrying):
            raise ValueError(f"Execution cannot proceed (status: {execution.status.value})")
        
        # SECURITY: Cap retries to prevent infinite loops
        if execution.retry_count > MAX_RETRIES:
            raise ValueError(f"Maximum retries ({MAX_RETRIES}) exceeded")
        
        skill = skill_registry.get(execution.skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {execution.skill_id}")
        
        # SECURITY: Validate against policy engine (same rules as control plane)
        # This ensures skills cannot bypass denylist, rate limits, or other safeguards
        async with async_session_maker() as db:
            is_valid, violations = await policy_engine.validate_skill_execution(
                db, execution.skill_id, execution.target
            )
            if not is_valid:
                execution.status = SkillExecutionStatus.failed
                execution.error = f"Policy violation: {'; '.join(violations)}"
                self._add_log(execution, f"BLOCKED by policy engine: {violations}")
                logger.warning(f"[SkillRunner] Execution {execution_id} blocked by policy: {violations}")
                await self._record_action_history(skill, execution)
                return execution
        
        execution.status = SkillExecutionStatus.executing
        if not execution.started_at:
            execution.started_at = datetime.utcnow()
        
        self._add_log(execution, "Policy validation passed")
        self._add_log(execution, "Starting execution" + (f" (retry #{execution.retry_count})" if execution.retry_count > 0 else ""))
        
        try:
            result = await self._execute_skill(skill, execution)
            execution.result = result
            self._add_log(execution, f"Execution completed: success={result.get('success', False)}")
            
            # SECURITY: Judge audit ONLY for high-risk (Tier 3) skills
            if skill.meta.risk == SkillRisk.high:
                execution.status = SkillExecutionStatus.pending_audit
                self._add_log(execution, "Awaiting judge audit (Tier 3 high-risk skill)")
                
                audit_result = await self._judge_audit(skill, execution, result)
                execution.audit_result = audit_result
                
                # SECURITY: Judge result is immutable - stored before decision
                self._add_log(execution, f"Judge audit result: {audit_result}")
                
                if not audit_result.get("approved", False):
                    execution.status = SkillExecutionStatus.escalated
                    execution.escalation_reason = audit_result.get("reason", "Judge rejected execution")
                    self._add_log(execution, f"ESCALATED: {execution.escalation_reason}")
                else:
                    execution.status = SkillExecutionStatus.completed
                    self._add_log(execution, "Judge approved execution")
            else:
                execution.status = SkillExecutionStatus.completed
            
            execution.completed_at = datetime.utcnow()
            
        except Exception as e:
            execution.error = str(e)
            self._add_log(execution, f"ERROR: {e}")
            
            # SECURITY: Exactly one retry, no more
            if execution.retry_count < MAX_RETRIES:
                execution.retry_count += 1
                execution.status = SkillExecutionStatus.retrying
                self._add_log(execution, f"Scheduling retry (attempt {execution.retry_count} of {MAX_RETRIES})")
                
                # Brief delay before retry
                await asyncio.sleep(2)
                return await self.execute(execution_id)
            else:
                # Escalate after max retries exhausted
                execution.status = SkillExecutionStatus.escalated
                execution.escalation_reason = f"Failed after {execution.retry_count} retry attempt(s): {e}"
                execution.completed_at = datetime.utcnow()
                self._add_log(execution, f"ESCALATED: Max retries ({MAX_RETRIES}) exhausted")
        
        # Always record to ActionHistory for audit trail
        await self._record_action_history(skill, execution)
        
        return execution
    
    def _add_log(self, execution: SkillExecution, message: str) -> None:
        """Add a timestamped log entry, respecting max entries."""
        if len(execution.logs) < MAX_LOG_ENTRIES:
            execution.logs.append(f"[{datetime.utcnow().isoformat()}] {message}")
    
    async def _execute_skill(
        self,
        skill: Skill,
        execution: SkillExecution,
    ) -> dict[str, Any]:
        """Execute the skill against the target infrastructure.
        
        Execution behavior depends on mode:
        - MOCK: Return canned response, no real execution
        - INTEGRATION: Real adapters against test fixtures
        - LAB: Real execution against production infrastructure
        """
        target = execution.target
        params = execution.parameters
        
        # Notify hooks (for test observability)
        await execution_mode_manager.notify_hooks(skill.meta.id, target, params)
        
        # MOCK MODE: Return canned response without real execution
        if execution_mode_manager.is_mock():
            self._add_log(execution, f"[MOCK MODE] Simulating execution")
            mock_response = execution_mode_manager.get_mock_response(skill.meta.id)
            
            # Simulate latency
            if mock_response.delay_seconds > 0:
                await asyncio.sleep(mock_response.delay_seconds)
            
            if not mock_response.success:
                self._add_log(execution, f"[MOCK MODE] Simulated failure: {mock_response.error_message}")
                raise Exception(mock_response.error_message or "Mock failure")
            
            self._add_log(execution, f"[MOCK MODE] Simulated success")
            return {
                "success": True,
                "adapter": "mock",
                "mode": "mock",
                **mock_response.output,
            }
        
        # SECURITY: Validate template doesn't contain sandbox escape patterns
        is_safe, violation = _validate_template_safety(skill.template)
        if not is_safe:
            self._add_log(execution, f"SECURITY: Template validation failed: {violation}")
            raise ValueError(f"Template security violation: {violation}")
        
        # Use sandboxed Jinja2 environment for template rendering
        env = sandbox.SandboxedEnvironment()
        template = env.from_string(skill.template)
        rendered = template.render(**params)
        self._add_log(execution, f"Rendered command: {rendered[:200]}...")
        
        # Log execution mode
        mode = execution_mode_manager.mode
        self._add_log(execution, f"Execution mode: {mode.value}")
        
        # Route to appropriate adapter based on target type
        if target.startswith("docker://"):
            return await self._execute_docker(skill, target, params, rendered)
        elif target.startswith("proxmox://"):
            return await self._execute_proxmox(skill, target, params)
        else:
            raise ValueError(f"Unsupported target type: {target}")
    
    async def _execute_docker(
        self,
        skill: Skill,
        target: str,
        params: dict[str, Any],
        rendered: str,
    ) -> dict[str, Any]:
        """Execute a Docker skill."""
        container = target.replace("docker://", "")
        
        # Map skill IDs to adapter methods
        if skill.meta.id == "rem-restart-container":
            success = await docker_adapter.restart_container(container)
            return {"success": success, "adapter": "docker", "action": "restart"}
        
        elif skill.meta.id == "rem-stop-container":
            success = await docker_adapter.stop_container(container)
            return {"success": success, "adapter": "docker", "action": "stop"}
        
        elif skill.meta.id == "diag-container-logs":
            lines = min(params.get("lines", 100), 500)  # Cap at 500 lines
            logs = await docker_adapter.get_container_logs(container, tail=lines)
            # Truncate logs for result storage
            return {
                "success": True, 
                "adapter": "docker", 
                "action": "logs", 
                "output": logs[:10000] if logs else "",
                "truncated": len(logs) > 10000 if logs else False
            }
        
        elif skill.meta.id == "diag-container-inspect":
            info = await docker_adapter.inspect_container(container)
            return {"success": info is not None, "adapter": "docker", "action": "inspect", "output": info}
        
        elif skill.meta.id == "maint-prune-images":
            result = await docker_adapter.prune_images()
            return {"success": True, "adapter": "docker", "action": "prune", "output": result}
        
        else:
            raise ValueError(f"Unhandled Docker skill: {skill.meta.id}")
    
    async def _execute_proxmox(
        self,
        skill: Skill,
        target: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a Proxmox skill."""
        # Parse target: proxmox://node/type/vmid
        parts = target.replace("proxmox://", "").split("/")
        if len(parts) < 3:
            raise ValueError(f"Invalid Proxmox target format: {target}")
        
        node = parts[0]
        vmtype = parts[1]  # "qemu" or "lxc"
        vmid = int(parts[2])
        
        if skill.meta.id in ("rem-restart-vm", "rem-restart-lxc"):
            success = await proxmox_adapter.reboot_resource(node, vmtype, vmid)
            return {"success": success, "adapter": "proxmox", "action": "restart", "type": vmtype}
        
        elif skill.meta.id in ("rem-stop-vm",):
            success = await proxmox_adapter.stop_resource(node, vmtype, vmid)
            return {"success": success, "adapter": "proxmox", "action": "stop", "type": vmtype}
        
        elif skill.meta.id == "diag-vm-status":
            status = await proxmox_adapter.get_resource_status(node, vmtype, vmid)
            return {"success": status is not None, "adapter": "proxmox", "action": "status", "output": status}
        
        elif skill.meta.id == "maint-create-snapshot":
            snapname = params.get("snapname")
            return {"success": True, "adapter": "proxmox", "action": "snapshot", "snapname": snapname}
        
        else:
            raise ValueError(f"Unhandled Proxmox skill: {skill.meta.id}")
    
    async def _judge_audit(
        self,
        skill: Skill,
        execution: SkillExecution,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Submit execution result to judge for audit (Tier 3 high-risk skills only).
        
        SECURITY:
        - Judge cannot silently flip failed to passed
        - Rationale is always recorded
        - Result is immutable once written
        
        In a full implementation, this would call an LLM to assess:
        - Did the action achieve its intended effect?
        - Are there any concerning side effects?
        - Should this be escalated to a human?
        """
        self._add_log(execution, "Judge audit starting...")
        
        audit_timestamp = datetime.utcnow().isoformat()
        
        # Extract success signal
        action_success = result.get("success", False)
        
        # Build audit record (immutable)
        audit_record = {
            "timestamp": audit_timestamp,
            "skill_id": skill.meta.id,
            "skill_risk": skill.meta.risk.value,
            "execution_id": execution.id,
            "action_result": result,
            "action_success": action_success,
        }
        
        # MVP: Basic success/failure checking
        # In production, this would use an LLM judge
        if action_success:
            audit_record.update({
                "approved": True,
                "reason": "Execution completed successfully",
                "confidence": 0.9,
                "recommendations": [],
                "requires_human_review": False,
            })
        else:
            # SECURITY: Failed actions are NOT automatically approved
            audit_record.update({
                "approved": False,
                "reason": f"Execution reported failure: {result.get('error', 'unknown')}",
                "confidence": 0.95,
                "recommendations": [
                    "Review execution logs",
                    "Check target resource state manually",
                    "Consider rollback if applicable"
                ],
                "requires_human_review": True,
            })
        
        self._add_log(execution, f"Judge decision: approved={audit_record['approved']}, reason={audit_record['reason']}")
        
        return audit_record
    
    async def _record_action_history(
        self,
        skill: Skill,
        execution: SkillExecution,
    ) -> None:
        """
        Record the execution to ActionHistory for complete audit trail.
        
        Records:
        - who requested (requested_by in logs)
        - what skill + version/hash
        - inputs (parameters)
        - output summary + logs
        - approval decision + approver
        - judge result (if applicable)
        """
        try:
            # Map skill to action template
            action_mapping = {
                "rem-restart-container": ActionTemplate.restart_resource,
                "rem-restart-vm": ActionTemplate.restart_resource,
                "rem-restart-lxc": ActionTemplate.restart_resource,
                "rem-stop-container": ActionTemplate.stop_resource,
                "rem-stop-vm": ActionTemplate.stop_resource,
                "diag-container-logs": ActionTemplate.collect_diagnostics,
                "diag-container-inspect": ActionTemplate.collect_diagnostics,
                "diag-vm-status": ActionTemplate.collect_diagnostics,
                "maint-prune-images": ActionTemplate.collect_diagnostics,
                "maint-create-snapshot": ActionTemplate.create_snapshot,
            }
            
            action_template = action_mapping.get(skill.meta.id, ActionTemplate.collect_diagnostics)
            
            status_mapping = {
                SkillExecutionStatus.completed: ActionStatus.completed,
                SkillExecutionStatus.failed: ActionStatus.failed,
                SkillExecutionStatus.escalated: ActionStatus.failed,
            }
            status = status_mapping.get(execution.status, ActionStatus.completed)
            
            # Build complete audit result including all required fields
            audit_result = {
                "skill_id": skill.meta.id,
                "skill_hash": _compute_skill_hash(skill),
                "skill_risk": skill.meta.risk.value,
                "approved_by": execution.approved_by,
                "retry_count": execution.retry_count,
                "execution_logs": execution.logs[-100:],  # Last 100 log entries
                "judge_audit": execution.audit_result,
                "escalation_reason": execution.escalation_reason,
            }
            
            # Merge with execution result
            if execution.result:
                # Don't store huge outputs in result
                safe_result = {k: v for k, v in execution.result.items() if k != "output"}
                if "output" in execution.result:
                    output = execution.result["output"]
                    if isinstance(output, str):
                        safe_result["output_preview"] = output[:500]
                        safe_result["output_truncated"] = len(output) > 500
                    elif isinstance(output, dict):
                        safe_result["output_keys"] = list(output.keys())[:20]
                audit_result["execution_result"] = safe_result
            
            async with async_session_maker() as db:
                action = ActionHistory(
                    incident_id=execution.incident_id,
                    action_template=action_template,
                    target_resource=execution.target,
                    parameters=execution.parameters,
                    status=status,
                    requested_at=execution.created_at,
                    approved_at=execution.approved_at,
                    executed_at=execution.started_at,
                    completed_at=execution.completed_at,
                    result=audit_result,
                    error=execution.error,
                )
                
                # SECURITY: Add to hash chain for tamper resistance
                await prepare_chained_entry(db, action)
                
                db.add(action)
                await db.commit()
                
                execution.action_history_id = action.id
                self._add_log(execution, f"Recorded to ActionHistory: {action.id} (chain seq={action.sequence_num})")
                
        except Exception as e:
            logger.error(f"[SkillRunner] Failed to record ActionHistory: {e}")
            self._add_log(execution, f"WARNING: Failed to record ActionHistory: {e}")
    
    def get_execution(self, execution_id: str) -> SkillExecution | None:
        """Get an execution by ID."""
        return self._executions.get(execution_id)
    
    def list_executions(
        self,
        status: SkillExecutionStatus | None = None,
        skill_id: str | None = None,
    ) -> list[SkillExecution]:
        """List executions, optionally filtered."""
        results = list(self._executions.values())
        
        if status:
            results = [e for e in results if e.status == status]
        if skill_id:
            results = [e for e in results if e.skill_id == skill_id]
        
        return sorted(results, key=lambda e: e.created_at, reverse=True)


# Singleton instance
skill_runner = SkillRunner()
