from __future__ import annotations

import asyncio

from worker.config import WorkerSettings
from worker.main import WorkerService


def test_worker_settings_defaults_enforce_phase1_constraints():
    settings = WorkerSettings()

    assert settings.mode == "worker"
    assert settings.allow_cloud_llm is False


def test_worker_service_heartbeat_and_shutdown(monkeypatch):
    settings = WorkerSettings(worker_id="test-worker", site="lab")
    service = WorkerService(settings=settings)

    heartbeat_calls: list[str] = []

    async def fake_heartbeat():
        heartbeat_calls.append("called")

    monkeypatch.setattr(service.client, "send_heartbeat", fake_heartbeat)

    async def _run() -> None:
        task = asyncio.create_task(service.run())
        await asyncio.sleep(0.05)
        service.request_shutdown()
        await asyncio.wait_for(task, timeout=1.0)

    asyncio.run(_run())

    assert heartbeat_calls == ["called"]
