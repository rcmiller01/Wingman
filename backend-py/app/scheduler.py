"""Background scheduler for periodic tasks."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.storage.database import async_session_maker
from app.collectors import fact_collector, log_collector


scheduler = AsyncIOScheduler()


async def collect_facts_job():
    """Periodic job to collect infrastructure facts."""
    async with async_session_maker() as db:
        try:
            counts = await fact_collector.collect_all(db)
            await db.commit()
            print(f"[Scheduler] Collected facts: {counts}")
        except Exception as e:
            print(f"[Scheduler] Fact collection failed: {e}")
            await db.rollback()


async def collect_logs_job():
    """Periodic job to collect container logs."""
    async with async_session_maker() as db:
        try:
            results = await log_collector.collect_all_container_logs(
                db, 
                since_minutes=5,  # Collect last 5 minutes
            )
            await db.commit()
            total = sum(results.values())
            if total > 0:
                print(f"[Scheduler] Collected {total} logs from {len(results)} containers")
        except Exception as e:
            print(f"[Scheduler] Log collection failed: {e}")
            await db.rollback()


async def purge_expired_logs_job():
    """Daily job to purge expired logs."""
    async with async_session_maker() as db:
        try:
            count = await log_collector.purge_expired_logs(db)
            await db.commit()
            if count > 0:
                print(f"[Scheduler] Purged {count} expired logs")
        except Exception as e:
            print(f"[Scheduler] Log purge failed: {e}")
            await db.rollback()


def start_scheduler():
    """Initialize and start the background scheduler."""
    # Collect facts every 60 seconds
    scheduler.add_job(
        collect_facts_job,
        trigger=IntervalTrigger(seconds=60),
        id="collect_facts",
        replace_existing=True,
    )
    
    # Collect logs every 5 minutes
    scheduler.add_job(
        collect_logs_job,
        trigger=IntervalTrigger(minutes=5),
        id="collect_logs",
        replace_existing=True,
    )
    
    # Purge expired logs daily
    scheduler.add_job(
        purge_expired_logs_job,
        trigger=IntervalTrigger(hours=24),
        id="purge_logs",
        replace_existing=True,
    )
    
    scheduler.start()
    print("[Scheduler] Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    print("[Scheduler] Background scheduler stopped")
