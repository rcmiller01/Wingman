"""Worker queue and registry service layer."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.models import (
    WorkerNode,
    WorkerResult,
    WorkerStatus,
    WorkerTask,
    WorkerTaskStatus,
)
from homelab.workers.schemas import WorkerResultEnvelope, WorkerTaskEnvelope


NOTIFY_CHANNEL = "worker_task"


async def enqueue_worker_task(
    db: AsyncSession,
    *,
    task_type: str,
    worker_id: str,
    idempotency_key: str,
    payload: dict,
    timeout_seconds: int = 60,
    site_name: str = "default",
    max_attempts: int = 3,
) -> WorkerTask:
    task = WorkerTask(
        task_type=task_type,
        worker_id=worker_id,
        idempotency_key=idempotency_key,
        payload=payload,
        timeout_seconds=timeout_seconds,
        site_name=site_name,
        max_attempts=max_attempts,
        status=WorkerTaskStatus.queued,
    )
    db.add(task)
    await db.flush()
    await db.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": NOTIFY_CHANNEL, "payload": json.dumps({"task_id": task.id})},
    )
    return task


async def claim_next_task(db: AsyncSession, *, worker_id: str) -> WorkerTaskEnvelope | None:
    now = datetime.utcnow()
    query = (
        select(WorkerTask)
        .where(
            WorkerTask.worker_id == worker_id,
            WorkerTask.status == WorkerTaskStatus.queued,
            ((WorkerTask.next_retry_at.is_(None)) | (WorkerTask.next_retry_at <= now)),
        )
        .order_by(WorkerTask.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    if task is None:
        return None

    task.status = WorkerTaskStatus.claimed
    task.claimed_at = now
    task.attempts += 1
    await db.flush()

    return WorkerTaskEnvelope(
        task_id=task.id,
        task_type=task.task_type,
        idempotency_key=task.idempotency_key,
        worker_id=task.worker_id,
        site_name=task.site_name,
        created_at=task.created_at,
        timeout_seconds=task.timeout_seconds,
        payload=task.payload,
    )


async def mark_task_running(db: AsyncSession, task_id: str) -> None:
    task = await db.get(WorkerTask, task_id)
    if not task:
        return
    task.status = WorkerTaskStatus.running
    task.started_at = datetime.utcnow()
    await db.flush()


async def submit_worker_result(db: AsyncSession, result: WorkerResultEnvelope) -> WorkerResult:
    existing = await db.execute(
        select(WorkerResult).where(
            WorkerResult.task_id == result.task_id,
            WorkerResult.idempotency_key == result.idempotency_key,
        )
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row:
        return existing_row

    row = WorkerResult(
        task_id=result.task_id,
        worker_id=result.worker_id,
        payload_type=result.payload_type,
        idempotency_key=result.idempotency_key,
        payload=result.payload,
        received_at=result.timestamp,
    )
    db.add(row)

    task = await db.get(WorkerTask, result.task_id)
    if task:
        success = bool(result.payload.get("success", True))
        task.status = WorkerTaskStatus.done if success else WorkerTaskStatus.failed
        task.completed_at = datetime.utcnow()
        task.error = None if success else str(result.payload.get("error") or "worker execution failed")

    await db.flush()
    return row


async def requeue_task_with_backoff(db: AsyncSession, task_id: str, reason: str) -> WorkerTask | None:
    task = await db.get(WorkerTask, task_id)
    if not task:
        return None

    task.error = reason
    if task.attempts >= task.max_attempts:
        task.status = WorkerTaskStatus.dead_letter
    else:
        task.status = WorkerTaskStatus.queued
        backoff_seconds = 2 ** max(task.attempts, 1)
        task.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
    await db.flush()
    return task


async def register_worker(
    db: AsyncSession,
    *,
    worker_id: str,
    site_name: str,
    capabilities: dict,
) -> WorkerNode:
    worker = await db.get(WorkerNode, worker_id)
    now = datetime.utcnow()
    if worker is None:
        worker = WorkerNode(
            worker_id=worker_id,
            site_name=site_name,
            capabilities=capabilities,
            status=WorkerStatus.online,
            last_seen=now,
            created_at=now,
            updated_at=now,
        )
        db.add(worker)
    else:
        worker.site_name = site_name
        worker.capabilities = capabilities
        worker.status = WorkerStatus.online
        worker.last_seen = now
        worker.updated_at = now

    await db.flush()
    return worker


async def list_worker_health(db: AsyncSession) -> dict:
    rows = (await db.execute(select(WorkerNode))).scalars().all()
    now = datetime.utcnow()
    workers = []
    for row in rows:
        freshness_seconds = (now - row.last_seen).total_seconds()
        computed_status = "online" if freshness_seconds <= 90 else "offline"
        workers.append(
            {
                "worker_id": row.worker_id,
                "site_name": row.site_name,
                "status": computed_status,
                "last_seen": row.last_seen.isoformat(),
                "capabilities": row.capabilities,
            }
        )

    queue_depth = (
        await db.execute(
            select(func.count()).select_from(WorkerTask).where(WorkerTask.status == WorkerTaskStatus.queued)
        )
    ).scalar_one()

    return {"workers": workers, "queue_depth": queue_depth}
