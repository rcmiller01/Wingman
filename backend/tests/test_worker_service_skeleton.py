from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone

import httpx

from worker.config import WorkerSettings
from worker.main import WorkerService
from homelab.workers.schemas import WorkerTaskEnvelope


def test_worker_settings_defaults_enforce_phase1_constraints():
    settings = WorkerSettings()

    assert settings.mode == "worker"
    assert settings.allow_cloud_llm is False


def test_worker_service_registers_processes_task_and_shuts_down(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = WorkerSettings(
            worker_id="test-worker",
            site="lab",
            poll_interval_seconds=0.01,
            heartbeat_interval_seconds=0.01,
            offline_dir=tmpdir,
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

        async def fake_register(**_kwargs):
            calls.append("register")

        async def fake_heartbeat(**_kwargs):
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

        async def fake_submit_envelope(_envelope):
            calls.append("submit")

        monkeypatch.setattr(service.client, "register", fake_register)
        monkeypatch.setattr(service.client, "send_heartbeat", fake_heartbeat)
        monkeypatch.setattr(service.client, "claim_task", fake_claim_task)
        monkeypatch.setattr(service.runner, "run", fake_runner_run)
        monkeypatch.setattr(service.client, "submit_envelope", fake_submit_envelope)

        asyncio.run(service.run())

        assert "register" in calls
        assert "heartbeat" in calls
        assert "run" in calls
        assert "submit" in calls


def test_worker_service_buffers_and_replays_on_connection_failure(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = WorkerSettings(worker_id="w1", site="lab", offline_dir=tmpdir)
        service = WorkerService(settings=settings)

        envelope = {
            "worker_id": "w1",
            "site_name": "lab",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload_type": "execution_result",
            "task_id": "t1",
            "idempotency_key": "t1:1",
            "payload": {"success": True},
        }

        attempts = {"count": 0}

        async def flaky_submit(_envelope):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise httpx.ConnectError("offline")
            return {"ok": True}

        monkeypatch.setattr(service.client, "submit_envelope", flaky_submit)

        async def _run():
            await service._submit_or_buffer(envelope)
            assert service.offline_buffer.backlog_size() == 1
            await service._replay_offline_buffer()

        asyncio.run(_run())
        assert service.offline_buffer.backlog_size() == 0
