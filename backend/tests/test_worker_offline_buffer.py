from __future__ import annotations

from datetime import datetime, timezone

from worker.offline import OfflineBuffer, OfflineBufferConfig


def test_offline_buffer_newest_first_and_ack(tmp_path):
    buffer = OfflineBuffer(OfflineBufferConfig(directory=tmp_path, max_files=10, max_age_seconds=3600))

    e1 = {
        "payload_type": "facts",
        "task_id": "task-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    e2 = {
        "payload_type": "execution_result",
        "task_id": "task-2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    p1 = buffer.write(e1)
    p2 = buffer.write(e2)

    pending = buffer.list_pending()
    assert pending[0].name >= pending[1].name

    loaded = buffer.load(pending[0])
    assert loaded["task_id"] in {"task-1", "task-2"}

    buffer.ack_delete(p1)
    assert p1.exists() is False
    assert buffer.backlog_size() == 1

    buffer.ack_delete(p2)
    assert buffer.backlog_size() == 0
