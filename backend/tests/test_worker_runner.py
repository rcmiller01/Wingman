from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import worker.runner as runner_module
from worker.runner import TaskRunner
from homelab.workers.schemas import WorkerTaskEnvelope


class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None


def test_task_runner_collect_facts(monkeypatch):
    task = WorkerTaskEnvelope(
        task_id="task-facts",
        task_type="collect_facts",
        idempotency_key="task-facts:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={},
    )

    async def fake_collect_all(_db):
        return {"docker": 2, "proxmox": 1}

    monkeypatch.setattr(runner_module, "async_session_maker", lambda: DummySession())
    monkeypatch.setattr(runner_module.fact_collector, "collect_all", fake_collect_all)

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "facts"
    assert payload["success"] is True
    assert payload["collected_counts"] == {"docker": 2, "proxmox": 1}


def test_task_runner_unknown_task_type():
    task = WorkerTaskEnvelope(
        task_id="task-unknown",
        task_type="does_not_exist",
        idempotency_key="task-unknown:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={},
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
