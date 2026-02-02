"""Control Plane - The Brain of the Homelab Copilot.

This module implements the core state machine that drives the autonomous loop.
States: OBSERVE -> ASSESS -> PLAN -> VALIDATE -> TODO -> APPROVAL -> EXECUTE -> VERIFY -> RECORD
"""

import asyncio
from enum import Enum
from datetime import datetime
import logging
import time

from homelab.storage.database import async_session_maker
from homelab.collectors import fact_collector, log_collector
from homelab.control_plane import incident_detector, plan_generator, plan_executor

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
                total_logs = sum(log_counts.values())
                if total_logs > 0:
                    print(f"[ControlPlane] Collected {total_logs} new logs")
                
                # 2. ASSESS
                await self._transition_to(ControlPlaneState.ASSESS)
                # In Phase 1: Detect incidents
                new_incidents = await incident_detector.detect_all(db)
                if new_incidents:
                    print(f"[ControlPlane] Detected {len(new_incidents)} new incidents")
                    # NEW: Dispatch alerts immediately
                    from homelab.notifications.router import notification_router  # Lazy import to avoid circular dep
                    for incident_data in new_incidents:
                        # Fetch the full incident object
                        incident = await incident_detector._get_open_incident(db, incident_data["resource"])
                        if incident:
                           await notification_router.notify_incident(incident)
                
                # 3. PLAN
                await self._transition_to(ControlPlaneState.PLAN)
                # No-op for skeleton, or call plan_generator if ready
                
                # 4. VALIDATE
                await self._transition_to(ControlPlaneState.VALIDATE)
                
                # 5. TODO
                await self._transition_to(ControlPlaneState.TODO)
                
                # 6. APPROVAL
                await self._transition_to(ControlPlaneState.APPROVAL)
                
                # 7. EXECUTE
                await self._transition_to(ControlPlaneState.EXECUTE)
                
                # 8. VERIFY
                await self._transition_to(ControlPlaneState.VERIFY)
                
                # 9. RECORD
                await self._transition_to(ControlPlaneState.RECORD)
                # NEW: Generate narratives for open incidents with placeholder narratives
                from homelab.rag.narrative_generator import narrative_generator
                from homelab.storage.models import Incident, IncidentNarrative
                from sqlalchemy import select, or_
                
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
