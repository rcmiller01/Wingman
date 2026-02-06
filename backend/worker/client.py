"""Control-plane client abstraction for worker communication."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from homelab.workers.schemas import WorkerResultEnvelope, WorkerTaskEnvelope


class WorkerControlPlaneClient:
    """Client used by worker to communicate with the control plane.

    Uses a persistent httpx.AsyncClient for connection pooling across
    the worker's 2-second poll loop instead of creating one per request.
    """

    def __init__(self, base_url: str, worker_id: str, site: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.worker_id = worker_id
        self.site = site
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def register(self, capabilities: dict | None = None) -> dict:
        client = await self._get_client()
        response = await client.post(
            "/api/workers/register",
            json={"worker_id": self.worker_id, "site_name": self.site, "capabilities": capabilities or {}},
        )
        response.raise_for_status()
        return response.json()

    async def send_heartbeat(self, capabilities: dict | None = None) -> dict:
        client = await self._get_client()
        response = await client.post(
            "/api/workers/heartbeat",
            json={"worker_id": self.worker_id, "site_name": self.site, "capabilities": capabilities or {}},
        )
        response.raise_for_status()
        return response.json()

    async def claim_task(self) -> WorkerTaskEnvelope | None:
        client = await self._get_client()
        response = await client.post(
            "/api/workers/tasks/claim",
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
        return await self.submit_envelope(envelope.model_dump(mode="json"))

    async def submit_envelope(self, envelope: dict) -> dict:
        client = await self._get_client()
        response = await client.post(
            "/api/workers/results",
            json=envelope,
        )
        response.raise_for_status()
        return response.json()
