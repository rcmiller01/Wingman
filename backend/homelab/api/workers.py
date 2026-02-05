"""Worker registration, queue, and result APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.database import get_db
from homelab.workers.schemas import (
    WorkerClaimRequest,
    WorkerEnqueueRequest,
    WorkerHeartbeatRequest,
    WorkerRegistrationRequest,
    WorkerResultEnvelope,
)
from homelab.workers.service import (
    claim_next_task,
    enqueue_worker_task,
    get_worker_metrics,
    list_worker_health,
    mark_task_running,
    register_worker,
    submit_worker_result,
)

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.post("/register")
async def register_worker_endpoint(
    request: WorkerRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    worker = await register_worker(
        db,
        worker_id=request.worker_id,
        site_name=request.site_name,
        capabilities=request.capabilities,
    )
    return {"worker_id": worker.worker_id, "status": worker.status.value}


@router.post("/heartbeat")
async def worker_heartbeat_endpoint(
    request: WorkerHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    worker = await register_worker(
        db,
        worker_id=request.worker_id,
        site_name=request.site_name,
        capabilities=request.capabilities,
    )
    return {"worker_id": worker.worker_id, "status": worker.status.value, "last_seen": worker.last_seen}


@router.post("/tasks/enqueue")
async def enqueue_worker_task_endpoint(
    request: WorkerEnqueueRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    task = await enqueue_worker_task(
        db,
        task_type=request.task_type,
        worker_id=request.worker_id,
        idempotency_key=request.idempotency_key,
        payload=request.payload,
        timeout_seconds=request.timeout_seconds,
        site_name=request.site_name,
        max_attempts=request.max_attempts,
    )
    return {"task_id": task.id, "status": task.status.value}


@router.post("/tasks/claim")
async def claim_task_endpoint(
    request: WorkerClaimRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    task = await claim_next_task(db, worker_id=request.worker_id)
    if task is None:
        return {"task": None}
    await mark_task_running(db, task.task_id)
    return {"task": task.model_dump(mode="json")}


@router.post("/results")
async def submit_result_endpoint(
    request: WorkerResultEnvelope,
    db: AsyncSession = Depends(get_db),
) -> dict:
    stored = await submit_worker_result(db, request)
    return {"result_id": stored.id, "task_id": stored.task_id}


@router.get("/health")
async def worker_health_endpoint(db: AsyncSession = Depends(get_db)) -> dict:
    return await list_worker_health(db)


@router.get("/metrics")
async def worker_metrics_endpoint(db: AsyncSession = Depends(get_db)) -> dict:
    metrics = await get_worker_metrics(db)
    # aggregate offline backlog from worker-reported capabilities
    workers = (await list_worker_health(db)).get("workers", [])
    metrics["offline_backlog_size"] = sum((w.get("capabilities") or {}).get("offline_backlog_size", 0) for w in workers)
    return metrics
