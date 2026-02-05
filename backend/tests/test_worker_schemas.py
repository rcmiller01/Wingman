from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError

from homelab.workers.schemas import WorkerResultEnvelope, WorkerTaskEnvelope


def test_worker_task_envelope_validates_required_fields():
    envelope = WorkerTaskEnvelope(
        task_id="task-1",
        task_type="collect_facts",
        idempotency_key="task-1:1",
        worker_id="worker-1",
        created_at=datetime.now(timezone.utc),
        payload={"k": "v"},
    )

    assert envelope.task_type == "collect_facts"


def test_worker_result_envelope_payload_type_validation():
    try:
        WorkerResultEnvelope(
            worker_id="worker-1",
            site_name="default",
            timestamp=datetime.now(timezone.utc),
            payload_type="invalid_type",
            task_id="task-1",
            idempotency_key="task-1:1",
            payload={},
        )
        assert False, "expected validation error"
    except ValidationError:
        assert True
