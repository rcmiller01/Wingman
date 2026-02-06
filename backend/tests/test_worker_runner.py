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


def test_task_runner_execute_script_success():
    task = WorkerTaskEnvelope(
        task_id="task-script",
        task_type="execute_script",
        idempotency_key="task-script:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={"action": "run_bash", "target": "local://worker", "params": {"command": "echo hi", "timeout": 5}},
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is True
    assert payload["result"]["plugin_id"] == "script"


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


# ============================================================================
# TaskRunner._execute_action Tests (Critical Gap - 0% coverage)
# ============================================================================

def test_execute_action_success():
    """Test successful plugin action execution via execute_action."""
    task = WorkerTaskEnvelope(
        task_id="task-action-1",
        task_type="execute_action",
        idempotency_key="task-action-1:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "echo success", "timeout": 5},
        },
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is True
    assert payload["result"]["plugin_id"] == "script"


def test_execute_action_missing_plugin_id():
    """Test validation error when plugin_id is missing from payload."""
    task = WorkerTaskEnvelope(
        task_id="task-action-2",
        task_type="execute_action",
        idempotency_key="task-action-2:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "action": "run_bash",
            "target": "local://worker",
            # Missing plugin_id
        },
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert "plugin_id" in payload["error"]


def test_execute_action_missing_action():
    """Test validation error when action is missing from payload."""
    task = WorkerTaskEnvelope(
        task_id="task-action-3",
        task_type="execute_action",
        idempotency_key="task-action-3:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "target": "local://worker",
            # Missing action
        },
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert "action" in payload["error"]


def test_execute_action_plugin_not_found():
    """Test error when plugin doesn't exist in registry."""
    task = WorkerTaskEnvelope(
        task_id="task-action-4",
        task_type="execute_action",
        idempotency_key="task-action-4:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "nonexistent_plugin",
            "action": "some_action",
            "target": "local://worker",
        },
    )

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert "nonexistent_plugin" in payload["error"]


def test_execute_action_pre_validation_failure(monkeypatch):
    """Test pre-validation failure prevents execution."""
    from homelab.execution_plugins import execution_registry
    
    task = WorkerTaskEnvelope(
        task_id="task-action-5",
        task_type="execute_action",
        idempotency_key="task-action-5:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "echo test"},
        },
    )

    # Mock pre-validation to fail
    async def fake_validate_pre(_action):
        return False, "Pre-validation failed: invalid target"

    plugin = execution_registry.get("script")
    monkeypatch.setattr(plugin, "validate_pre", fake_validate_pre)

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert "Pre-validation failed" in payload["error"]


def test_execute_action_post_validation_failure_triggers_rollback(monkeypatch):
    """Test post-validation failure triggers plugin rollback."""
    from homelab.execution_plugins import execution_registry
    
    task = WorkerTaskEnvelope(
        task_id="task-action-6",
        task_type="execute_action",
        idempotency_key="task-action-6:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "echo test"},
        },
    )

    rollback_called = {"called": False}

    # Mock post-validation to fail
    async def fake_validate_post(_action, _result):
        return False, "Post-validation failed: unexpected output"

    async def fake_rollback(_action, _result):
        rollback_called["called"] = True

    plugin = execution_registry.get("script")
    monkeypatch.setattr(plugin, "validate_post", fake_validate_post)
    monkeypatch.setattr(plugin, "rollback", fake_rollback)

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "POSTCHECK_ERROR"
    assert "Post-validation failed" in payload["error"]
    assert rollback_called["called"] is True


def test_execute_action_execution_exception(monkeypatch):
    """Test generic exception during plugin execution."""
    from homelab.execution_plugins import execution_registry
    
    task = WorkerTaskEnvelope(
        task_id="task-action-7",
        task_type="execute_action",
        idempotency_key="task-action-7:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "echo test"},
        },
    )

    # Mock execute to raise exception
    async def fake_execute(_action):
        raise RuntimeError("Unexpected plugin error")

    plugin = execution_registry.get("script")
    monkeypatch.setattr(plugin, "execute", fake_execute)

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "EXECUTION_ERROR"
    assert "Unexpected plugin error" in payload["error"]


def test_execute_action_timeout_error(monkeypatch):
    """Test timeout during plugin execution."""
    from homelab.execution_plugins import execution_registry
    
    task = WorkerTaskEnvelope(
        task_id="task-action-8",
        task_type="execute_action",
        idempotency_key="task-action-8:1",
        worker_id="w1",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "sleep 100"},
        },
    )

    # Mock execute to raise TimeoutError
    async def fake_execute(_action):
        raise TimeoutError("Plugin execution timed out")

    plugin = execution_registry.get("script")
    monkeypatch.setattr(plugin, "execute", fake_execute)

    payload_type, payload = asyncio.run(TaskRunner().run(task))

    assert payload_type == "execution_result"
    assert payload["success"] is False
    assert payload["error_code"] == "TIMEOUT_ERROR"
    assert "timed out" in payload["error"].lower()


def test_execute_action_metadata_propagation():
    """Test that task metadata is propagated to plugin action."""
    from homelab.execution_plugins import execution_registry
    from unittest.mock import AsyncMock, patch
    
    task = WorkerTaskEnvelope(
        task_id="task-action-9",
        task_type="execute_action",
        idempotency_key="task-action-9:1",
        worker_id="worker-123",
        site_name="default",
        created_at=datetime.now(timezone.utc),
        timeout_seconds=20,
        payload={
            "plugin_id": "script",
            "action": "run_bash",
            "target": "local://worker",
            "params": {"command": "echo metadata"},
            "action_id": "action-456",
            "todo_id": "todo-789",
        },
    )

    captured_action = {"action": None}

    # Capture the PluginAction passed to execute
    original_execute = execution_registry.get("script").execute

    async def capture_execute(action):
        captured_action["action"] = action
        return await original_execute(action)

    with patch.object(execution_registry.get("script"), "execute", side_effect=capture_execute):
        asyncio.run(TaskRunner().run(task))

    # Verify metadata was propagated
    assert captured_action["action"] is not None
    metadata = captured_action["action"].metadata
    assert metadata["task_id"] == "task-action-9"
    assert metadata["worker_id"] == "worker-123"
    assert metadata["source"] == "worker"
    assert metadata["action_id"] == "action-456"
    assert metadata["todo_id"] == "todo-789"

