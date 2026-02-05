"""Control-plane client abstraction for worker communication."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from homelab.workers.schemas import WorkerResultEnvelope, WorkerTaskEnvelope


class WorkerControlPlaneClient:
    """Client used by worker to communicate with the control plane."""

    def __init__(self, base_url: str, worker_id: str, site: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.worker_id = worker_id
        self.site = site

    async def register(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/workers/register",
                json={"worker_id": self.worker_id, "site_name": self.site, "capabilities": {}},
            )
            response.raise_for_status()
            return response.json()

    async def send_heartbeat(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/workers/heartbeat",
                json={"worker_id": self.worker_id, "site_name": self.site, "capabilities": {}},
            )
            response.raise_for_status()
            return response.json()

    async def claim_task(self) -> WorkerTaskEnvelope | None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/workers/tasks/claim",
                json={"worker_id": self.worker_id},
            )
            response.raise_for_status()
            payload = response.json()
            task = payload.get("task")
            if task is None:
                return None
            return WorkerTaskEnvelope.model_validate(task)

    async def submit_result(self, *, task: WorkerTaskEnvelope, payload_type: str, payload: dict) -> dict:
        envelope = WorkerResultEnvelope(
            worker_id=self.worker_id,
            site_name=self.site,
            timestamp=datetime.now(timezone.utc),
            payload_type=payload_type,
            task_id=task.task_id,
            idempotency_key=task.idempotency_key,
            payload=payload,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/workers/results",
                json=envelope.model_dump(mode="json"),
            )
            response.raise_for_status()
            return response.json()
