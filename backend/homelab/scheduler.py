"""Background scheduler for periodic tasks."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from homelab.storage.database import async_session_maker
from homelab.collectors import fact_collector, log_collector
from homelab.control_plane import incident_detector



from homelab.control_plane.control_plane import control_plane

scheduler = AsyncIOScheduler()

async def run_control_plane_loop():
    """Execute the unified control plane loop."""
    await control_plane.run_loop()

def start_scheduler():
    """Initialize and start the background scheduler."""
    # Run the full Control Plane loop every 60 seconds
    scheduler.add_job(
        run_control_plane_loop,
        trigger=IntervalTrigger(seconds=60),
        id="control_plane_loop",
        replace_existing=True,
    )
    
    scheduler.start()
    print("[Scheduler] Background scheduler started (Control Plane Loop: 60s)")

def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    print("[Scheduler] Background scheduler stopped")
