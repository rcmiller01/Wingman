"""Task dispatch router for worker runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkerTask:
    """Minimal worker task envelope placeholder for Ticket 6."""

    task_id: str
    task_type: str
    payload: dict[str, Any]


class TaskRunner:
    """Routes tasks to execution handlers."""

    async def run(self, task: WorkerTask) -> dict[str, Any]:
        logger.info(
            "worker_task_received",
            extra={"task_id": task.task_id, "task_type": task.task_type},
        )

        return {
            "task_id": task.task_id,
            "status": "not_implemented",
            "message": "Task execution handlers will be implemented in PH1-WKR-007+",
        }
