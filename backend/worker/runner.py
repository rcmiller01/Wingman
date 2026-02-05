"""Task dispatch router for worker runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homelab.collectors.fact_collector import fact_collector
from homelab.storage.database import async_session_maker
from homelab.workers.schemas import WorkerTaskEnvelope


class TaskRunner:
    """Routes tasks to execution handlers."""

    async def run(self, task: WorkerTaskEnvelope) -> tuple[str, dict[str, Any]]:
        if task.task_type == "collect_facts":
            return await self._collect_facts(task)

        return "execution_result", {
            "success": False,
            "error": f"Unsupported task type: {task.task_type}",
            "task_type": task.task_type,
        }

    async def _collect_facts(self, task: WorkerTaskEnvelope) -> tuple[str, dict[str, Any]]:
        async with async_session_maker() as session:
            counts = await fact_collector.collect_all(session)
            await session.commit()

        return "facts", {
            "success": True,
            "task_id": task.task_id,
            "collected_counts": counts,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
