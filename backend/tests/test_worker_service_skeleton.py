from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from worker.config import WorkerSettings
from worker.main import WorkerService
from homelab.workers.schemas import WorkerTaskEnvelope


def test_worker_settings_defaults_enforce_phase1_constraints():
    settings = WorkerSettings()

    assert settings.mode == "worker"
    assert settings.allow_cloud_llm is False


def test_worker_service_registers_processes_task_and_shuts_down(monkeypatch):
    settings = WorkerSettings(
        worker_id="test-worker",
        site="lab",
        poll_interval_seconds=0.01,
        heartbeat_interval_seconds=0.01,
    )
    service = WorkerService(settings=settings)

    calls: list[str] = []
    task = WorkerTaskEnvelope(
        task_id="task-1",
        task_type="collect_facts",
        idempotency_key="task-1:1",
        worker_id="test-worker",
        site_name="lab",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=30,
        payload={},
    )

    async def fake_register():
        calls.append("register")

    async def fake_heartbeat():
        calls.append("heartbeat")

    async def fake_claim_task():
        if "claimed" in calls:
            return None
        calls.append("claimed")
        return task

    async def fake_runner_run(_task):
        calls.append("run")
        service.request_shutdown()
        return "facts", {"success": True}

    async def fake_submit_result(**_kwargs):
        calls.append("submit")

    monkeypatch.setattr(service.client, "register", fake_register)
    monkeypatch.setattr(service.client, "send_heartbeat", fake_heartbeat)
    monkeypatch.setattr(service.client, "claim_task", fake_claim_task)
    monkeypatch.setattr(service.runner, "run", fake_runner_run)
    monkeypatch.setattr(service.client, "submit_result", fake_submit_result)

    asyncio.run(service.run())

    assert "register" in calls
    assert "heartbeat" in calls
    assert "run" in calls
    assert "submit" in calls
