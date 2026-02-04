"""Retention and cleanup policy for executions and logs.

Configurable retention windows:
- Executions: How long to keep execution records
- Logs: How long to keep collected log entries
- Audit entries: Kept longer for compliance (or exported)

AUDIT CHAIN PRESERVATION:
The audit chain (ActionHistory) has special handling to maintain tamper detection:
1. Never delete audit entries - only archive/export them
2. Keep genesis entry and periodic checkpoints forever
3. Export full history before any pruning
4. Verify chain integrity after any operation
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
import asyncio
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RetentionConfig:
    """Configuration for data retention windows."""
    
    # Execution retention
    execution_retention_days: int = 30
    completed_execution_retention_days: int = 7
    failed_execution_retention_days: int = 14
    
    # Log retention  
    log_retention_days: int = 7
    
    # Audit retention (longer for compliance)
    audit_retention_days: int = 90
    
    # Cleanup schedule
    cleanup_interval_hours: int = 6
    
    # Safety: dry run mode
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "RetentionConfig":
        """Load retention config from environment variables."""
        import os
        
        def get_int(key: str, default: int) -> int:
            value = os.environ.get(key, "")
            try:
                return int(value) if value else default
            except ValueError:
                return default
        
        return cls(
            execution_retention_days=get_int("RETENTION_EXECUTION_DAYS", 30),
            completed_execution_retention_days=get_int("RETENTION_COMPLETED_EXECUTION_DAYS", 7),
            failed_execution_retention_days=get_int("RETENTION_FAILED_EXECUTION_DAYS", 14),
            log_retention_days=get_int("RETENTION_LOG_DAYS", 7),
            audit_retention_days=get_int("RETENTION_AUDIT_DAYS", 90),
            cleanup_interval_hours=get_int("RETENTION_CLEANUP_INTERVAL_HOURS", 6),
            dry_run=os.environ.get("RETENTION_DRY_RUN", "").lower() in ("true", "1"),
        )


@dataclass
class CleanupStats:
    """Statistics from a cleanup run."""
    executions_deleted: int = 0
    logs_deleted: int = 0
    audit_exported: int = 0
    audit_checkpoints_kept: int = 0
    errors: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def total_deleted(self) -> int:
        return self.executions_deleted + self.logs_deleted
    
    def to_dict(self) -> dict:
        return {
            "executions_deleted": self.executions_deleted,
            "logs_deleted": self.logs_deleted,
            "audit_exported": self.audit_exported,
            "audit_checkpoints_kept": self.audit_checkpoints_kept,
            "total_deleted": self.total_deleted,
            "errors": self.errors,
        }


@dataclass
class AuditCheckpoint:
    """
    Checkpoint in the audit chain that must be preserved.
    
    Checkpoints anchor the hash chain verification - we keep:
    1. Genesis (sequence_num=1) - always
    2. Daily checkpoints - first entry of each day
    3. Monthly checkpoints - first entry of each month
    """
    sequence_num: int
    entry_hash: str
    timestamp: datetime
    checkpoint_type: str  # "genesis", "daily", "monthly"


class RetentionManager:
    """Manages data retention and cleanup."""
    
    def __init__(self, config: Optional[RetentionConfig] = None):
        self.config = config or RetentionConfig.from_env()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def get_cutoff_date(self, retention_days: int) -> datetime:
        """Calculate the cutoff date for retention.
        
        Returns naive datetime (UTC) for compatibility with database columns.
        """
        return datetime.utcnow() - timedelta(days=retention_days)
    
    async def cleanup_executions(self, executions: dict) -> int:
        """Clean up old executions from in-memory store.
        
        Different retention periods for different statuses:
        - completed: shorter retention (default 7 days)
        - failed: medium retention (default 14 days)  
        - other: longer retention (default 30 days)
        
        Returns count of deleted executions.
        """
        now = datetime.now(timezone.utc)
        to_delete = []
        
        for exec_id, record in executions.items():
            try:
                created_at = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
                status = record.get("status", "")
                
                # Determine retention based on status
                if status == "completed":
                    retention_days = self.config.completed_execution_retention_days
                elif status == "failed":
                    retention_days = self.config.failed_execution_retention_days
                else:
                    retention_days = self.config.execution_retention_days
                
                cutoff = now - timedelta(days=retention_days)
                
                if created_at < cutoff:
                    to_delete.append(exec_id)
                    
            except (ValueError, KeyError) as e:
                logger.warning(f"[Retention] Error checking execution {exec_id}: {e}")
        
        # Delete old executions
        deleted = 0
        for exec_id in to_delete:
            if self.config.dry_run:
                logger.info(f"[Retention] DRY RUN: Would delete execution {exec_id}")
            else:
                executions.pop(exec_id, None)
                deleted += 1
        
        if deleted > 0:
            logger.info(f"[Retention] Deleted {deleted} old executions")
        
        return deleted
    
    async def cleanup_logs_database(self, db_session) -> int:
        """Clean up old logs from database.
        
        This should be called with an async database session.
        Returns count of deleted log entries.
        """
        from sqlalchemy import delete, select, func
        from homelab.storage.models import LogEntry
        
        cutoff = self.get_cutoff_date(self.config.log_retention_days)
        
        try:
            if self.config.dry_run:
                # Count what would be deleted
                result = await db_session.execute(
                    select(func.count()).select_from(LogEntry).where(
                        LogEntry.timestamp < cutoff
                    )
                )
                count = result.scalar() or 0
                logger.info(f"[Retention] DRY RUN: Would delete {count} log entries")
                return 0
            
            # Delete old logs
            result = await db_session.execute(
                delete(LogEntry).where(LogEntry.timestamp < cutoff)
            )
            await db_session.commit()
            
            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"[Retention] Deleted {deleted} old log entries")
            
            return deleted
            
        except Exception as e:
            logger.error(f"[Retention] Error cleaning up logs: {e}")
            await db_session.rollback()
            raise
    
    async def export_audit_entries(self, db_session, export_path: str) -> int:
        """Export old audit entries before deletion.
        
        Entries older than audit_retention_days are exported to JSON
        for compliance/archival purposes.
        
        IMPORTANT: This exports but does NOT delete audit entries.
        Use safe_prune_audit_entries for deletion with chain preservation.
        """
        from sqlalchemy import select
        from homelab.storage.models import ActionHistory
        
        cutoff = self.get_cutoff_date(self.config.audit_retention_days)
        
        try:
            # Select old entries
            result = await db_session.execute(
                select(ActionHistory).where(
                    ActionHistory.requested_at < cutoff
                ).order_by(ActionHistory.sequence_num)
            )
            entries = result.scalars().all()
            
            if not entries:
                return 0
            
            # Export to JSON with full chain data
            export_data = {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "cutoff_date": cutoff.isoformat(),
                "entry_count": len(entries),
                "first_sequence": entries[0].sequence_num if entries else None,
                "last_sequence": entries[-1].sequence_num if entries else None,
                "entries": [],
            }
            
            for entry in entries:
                export_data["entries"].append({
                    "id": str(entry.id),
                    "incident_id": entry.incident_id,
                    "action_template": entry.action_template.value,
                    "target_resource": entry.target_resource,
                    "parameters": entry.parameters,
                    "status": entry.status.value if entry.status else None,
                    "requested_at": entry.requested_at.isoformat() if entry.requested_at else None,
                    "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
                    "executed_at": entry.executed_at.isoformat() if entry.executed_at else None,
                    "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                    "result": entry.result,
                    "error": entry.error,
                    # Actor attribution
                    "requested_by_user_id": entry.requested_by_user_id,
                    "requested_by_role": entry.requested_by_role,
                    "approved_by_user_id": entry.approved_by_user_id,
                    "approved_by_role": entry.approved_by_role,
                    # Hash chain data (CRITICAL for verification)
                    "prev_hash": entry.prev_hash,
                    "entry_hash": entry.entry_hash,
                    "sequence_num": entry.sequence_num,
                })
            
            if self.config.dry_run:
                logger.info(f"[Retention] DRY RUN: Would export {len(export_data['entries'])} audit entries")
                return 0
            
            # Ensure export directory exists
            Path(export_path).mkdir(parents=True, exist_ok=True)
            
            # Write to file
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{export_path}/audit_export_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"[Retention] Exported {len(export_data['entries'])} audit entries to {filename}")
            
            return len(export_data["entries"])
            
        except Exception as e:
            logger.error(f"[Retention] Error exporting audit entries: {e}")
            raise
    
    async def get_audit_checkpoints(self, db_session) -> list[AuditCheckpoint]:
        """
        Get audit chain checkpoints that must be preserved.
        
        Returns checkpoints for:
        - Genesis entry (sequence_num=1)
        - First entry of each day
        - First entry of each month
        """
        from sqlalchemy import select, func, extract
        from homelab.storage.models import ActionHistory
        
        checkpoints = []
        
        try:
            # Get genesis entry
            result = await db_session.execute(
                select(ActionHistory).where(ActionHistory.sequence_num == 1)
            )
            genesis = result.scalar_one_or_none()
            if genesis:
                checkpoints.append(AuditCheckpoint(
                    sequence_num=genesis.sequence_num,
                    entry_hash=genesis.entry_hash or "",
                    timestamp=genesis.requested_at,
                    checkpoint_type="genesis",
                ))
            
            # Get daily checkpoints (first entry of each day)
            # This is a simplified approach - in production, use a more efficient query
            result = await db_session.execute(
                select(ActionHistory).order_by(ActionHistory.sequence_num)
            )
            all_entries = result.scalars().all()
            
            seen_days = set()
            seen_months = set()
            
            for entry in all_entries:
                if not entry.requested_at:
                    continue
                
                day_key = entry.requested_at.strftime("%Y-%m-%d")
                month_key = entry.requested_at.strftime("%Y-%m")
                
                if day_key not in seen_days:
                    seen_days.add(day_key)
                    checkpoints.append(AuditCheckpoint(
                        sequence_num=entry.sequence_num,
                        entry_hash=entry.entry_hash or "",
                        timestamp=entry.requested_at,
                        checkpoint_type="daily",
                    ))
                
                if month_key not in seen_months:
                    seen_months.add(month_key)
                    checkpoints.append(AuditCheckpoint(
                        sequence_num=entry.sequence_num,
                        entry_hash=entry.entry_hash or "",
                        timestamp=entry.requested_at,
                        checkpoint_type="monthly",
                    ))
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"[Retention] Error getting audit checkpoints: {e}")
            return []
    
    async def safe_prune_audit_entries(
        self,
        db_session,
        export_path: str,
        preserve_checkpoints: bool = True,
    ) -> tuple[int, int]:
        """
        Safely prune old audit entries while preserving chain integrity.
        
        This method:
        1. Exports all entries being pruned
        2. Identifies checkpoints to preserve
        3. Only deletes non-checkpoint entries
        4. Verifies chain integrity after pruning
        
        Returns (entries_exported, entries_deleted).
        
        WARNING: This is a destructive operation. Use with caution.
        """
        from sqlalchemy import delete
        from homelab.storage.models import ActionHistory
        from homelab.storage.audit_chain import verify_chain_integrity
        
        cutoff = self.get_cutoff_date(self.config.audit_retention_days)
        
        # Step 1: Export everything first
        exported = await self.export_audit_entries(db_session, export_path)
        
        if self.config.dry_run:
            logger.info("[Retention] DRY RUN: Skipping audit deletion")
            return exported, 0
        
        # Step 2: Get checkpoints to preserve
        checkpoints = []
        if preserve_checkpoints:
            checkpoints = await self.get_audit_checkpoints(db_session)
            checkpoint_seqs = {cp.sequence_num for cp in checkpoints}
            logger.info(f"[Retention] Preserving {len(checkpoints)} audit checkpoints")
        else:
            checkpoint_seqs = set()
        
        # Step 3: Delete non-checkpoint entries older than cutoff
        # NOTE: We never delete entries - only archive them
        # This is a safety measure to maintain audit chain
        logger.warning(
            "[Retention] Audit entry deletion is disabled for chain integrity. "
            "Entries have been exported to archive. Manual cleanup requires "
            "setting RETENTION_ALLOW_AUDIT_DELETE=true and careful verification."
        )
        
        deleted = 0  # We don't actually delete - just export
        
        # Step 4: Verify chain integrity
        try:
            is_valid, violations = await verify_chain_integrity(db_session)
            if not is_valid:
                logger.error(f"[Retention] Chain integrity check failed: {violations}")
        except Exception as e:
            logger.error(f"[Retention] Chain integrity verification error: {e}")
        
        return exported, deleted
    
    async def verify_audit_integrity(self, db_session) -> dict:
        """
        Verify the audit chain integrity.
        
        Returns a report with:
        - is_valid: Whether the chain is intact
        - total_entries: Number of entries in the chain
        - violations: List of any integrity violations
        - checkpoints: List of preserved checkpoints
        """
        from homelab.storage.audit_chain import verify_chain_integrity
        from sqlalchemy import select, func
        from homelab.storage.models import ActionHistory
        
        try:
            # Get entry count
            result = await db_session.execute(
                select(func.count()).select_from(ActionHistory)
            )
            total_entries = result.scalar() or 0
            
            # Verify chain
            is_valid, violations = await verify_chain_integrity(db_session)
            
            # Get checkpoints
            checkpoints = await self.get_audit_checkpoints(db_session)
            
            return {
                "is_valid": is_valid,
                "total_entries": total_entries,
                "violations": violations,
                "checkpoints": [
                    {
                        "sequence_num": cp.sequence_num,
                        "entry_hash": cp.entry_hash[:16] + "..." if cp.entry_hash else None,
                        "timestamp": cp.timestamp.isoformat() if cp.timestamp else None,
                        "type": cp.checkpoint_type,
                    }
                    for cp in checkpoints
                ],
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"[Retention] Audit integrity check error: {e}")
            return {
                "is_valid": False,
                "total_entries": 0,
                "violations": [{"type": "error", "message": str(e)}],
                "checkpoints": [],
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
    
    async def run_cleanup(
        self,
        executions: Optional[dict] = None,
        db_session = None,
        export_path: Optional[str] = None,
    ) -> CleanupStats:
        """Run full cleanup cycle.
        
        Args:
            executions: In-memory executions dict (optional)
            db_session: Database session for log cleanup (optional)
            export_path: Path to export audit entries (optional)
            
        Returns:
            CleanupStats with results
        """
        stats = CleanupStats()
        
        logger.info("[Retention] Starting cleanup cycle...")
        
        # Clean up executions
        if executions is not None:
            try:
                stats.executions_deleted = await self.cleanup_executions(executions)
            except Exception as e:
                stats.errors.append(f"Execution cleanup failed: {e}")
        
        # Clean up logs
        if db_session is not None:
            try:
                stats.logs_deleted = await self.cleanup_logs_database(db_session)
            except Exception as e:
                stats.errors.append(f"Log cleanup failed: {e}")
        
        # Export audit entries
        if db_session is not None and export_path:
            try:
                stats.audit_exported = await self.export_audit_entries(db_session, export_path)
            except Exception as e:
                stats.errors.append(f"Audit export failed: {e}")
        
        logger.info(
            f"[Retention] Cleanup complete: "
            f"{stats.executions_deleted} executions, "
            f"{stats.logs_deleted} logs deleted, "
            f"{stats.audit_exported} audit entries exported"
        )
        
        return stats
    
    async def start_background_cleanup(
        self,
        executions_getter: Callable[[], dict],
        db_session_getter: Callable[[], Awaitable],
        export_path: Optional[str] = None,
    ):
        """Start background cleanup task.
        
        Args:
            executions_getter: Function to get the executions dict
            db_session_getter: Async function to get a database session
            export_path: Path for audit exports
        """
        if self._running:
            logger.warning("[Retention] Background cleanup already running")
            return
        
        self._running = True
        
        async def cleanup_loop():
            while self._running:
                try:
                    # Wait for next cleanup cycle
                    await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                    
                    if not self._running:
                        break
                    
                    # Run cleanup
                    executions = executions_getter()
                    async with await db_session_getter() as session:
                        await self.run_cleanup(
                            executions=executions,
                            db_session=session,
                            export_path=export_path,
                        )
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[Retention] Background cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(
            f"[Retention] Started background cleanup "
            f"(interval: {self.config.cleanup_interval_hours}h)"
        )
    
    async def stop_background_cleanup(self):
        """Stop background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("[Retention] Stopped background cleanup")


# Global retention manager instance
retention_manager = RetentionManager()
