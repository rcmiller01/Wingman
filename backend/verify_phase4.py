
import asyncio
import httpx
from datetime import datetime
from homelab.storage.database import async_session_maker
from homelab.storage.models import Incident, IncidentSeverity, IncidentStatus, ActionHistory, ActionStatus
from sqlalchemy import select

async def verify_guide_mode():
    incident_id = None
    
    # 1. Create Mock Incident
    async with async_session_maker() as db:
        print("[Verify] Creating mock restart loop incident...")
        incident = Incident(
            severity=IncidentSeverity.high,
            status=IncidentStatus.open,
            affected_resources=["docker://test-container-1"],
            symptoms=["Container test-container-1 has high restart count: 5"],
            detected_at=datetime.now(timezone.utc)
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        incident_id = incident.id
        print(f"[Verify] Created Incident {incident_id}")

    # 2. Monitor for Plan Creation (Wait up to 70s as loop runs every 60s)
    print("[Verify] Waiting for ControlPlane to propose plan (max 70s)...")
    plan_id = None
    
    for _ in range(14): # 14 * 5s = 70s
        await asyncio.sleep(5)
        async with async_session_maker() as db:
             result = await db.execute(select(ActionHistory).where(ActionHistory.incident_id == incident_id))
             plan = result.scalar_one_or_none()
             if plan:
                 print(f"[Verify] Plan Proposed! ID: {plan.id}, Template: {plan.action_template}")
                 plan_id = plan.id
                 break
    
    if not plan_id:
        print("[Verify] FAILED: No plan proposed after timeout.")
        return

    # 3. Approve Plan via API
    print(f"[Verify] Approving plan {plan_id} via API...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"http://localhost:8000/api/plans/{plan_id}/approve")
            if resp.status_code == 200:
                print("[Verify] Plan Approved successfully.")
            else:
                print(f"[Verify] Approval Failed: {resp.status_code} {resp.text}")
                return
    except Exception as e:
         print(f"[Verify] API Error: {e}")
         return

    # 4. Check Execution Status
    print("[Verify] Waiting for execution (max 70s)...")
    for _ in range(14):
        await asyncio.sleep(5)
        async with async_session_maker() as db:
             result = await db.execute(select(ActionHistory).where(ActionHistory.id == plan_id))
             plan = result.scalar_one_or_none()
             if plan.status in [ActionStatus.completed, ActionStatus.failed]:
                 print(f"[Verify] Execution Finished. Status: {plan.status}")
                 print(f"[Verify] Result: {plan.result}")
                 print(f"[Verify] Error: {plan.error}")
                 break
             else:
                 print(f"[Verify] Current Status: {plan.status}")

if __name__ == "__main__":
    asyncio.run(verify_guide_mode())
