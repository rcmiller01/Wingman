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
        logger.info("=== Starting Control Plane Loop ===")
        
        async with async_session_maker() as db:
            try:
                # 1. OBSERVE
                await self._transition_to(ControlPlaneState.OBSERVE)
                # In Phase 1: Call collectors purely for observation
                await fact_collector.collect_all(db)
                await log_collector.collect_all_container_logs(db, since_minutes=2)
                
                # 2. ASSESS
                await self._transition_to(ControlPlaneState.ASSESS)
                # In Phase 1: Detect incidents
                new_incidents = await incident_detector.detect_all(db)
                if new_incidents:
                    logger.info(f"Detected {len(new_incidents)} new incidents")
                
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
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error in Control Plane Loop: {e}", exc_info=True)
                await db.rollback()
            finally:
                duration = time.time() - start_time
                self.last_run = datetime.utcnow()
                logger.info(f"=== Control Plane Loop Completed in {duration:.2f}s ===\n")

    async def _transition_to(self, new_state: ControlPlaneState):
        """Log state transition."""
        logger.info(f"[State Transition] {self.current_state} -> {new_state}")
        self.current_state = new_state
        # Simulate minor checking delay
        # await asyncio.sleep(0.01)

# Singleton instance
control_plane = ControlPlane()
