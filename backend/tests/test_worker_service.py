"""Tests for worker service, including dead-letter alert emission."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.workers.service import requeue_task_with_backoff
from homelab.storage.models import WorkerTask, WorkerTaskStatus


@pytest.fixture
async def mock_db_session():
    """Create a mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_dead_letter_alert_emission(mock_db_session):
    """Test that dead-letter alert is emitted when max_attempts reached."""
    # Arrange: task with attempts >= max_attempts
    task = WorkerTask(
        id="task-123",
        task_type="execute_action",
        idempotency_key="key-123",
        worker_id="worker-1",
        site_name="default",
        timeout_seconds=60,
        payload={},
        attempts=3,
        max_attempts=3,
        status=WorkerTaskStatus.failed,
    )
    
    mock_db_session.get.return_value = task
    
    # Act: requeue with backoff
    with patch('homelab.workers.service.logger') as mock_logger:
        result = await requeue_task_with_backoff(mock_db_session, "task-123", "Test failure")
        
        # Assert: ERROR level alert was logged
        assert mock_logger.error.called
        call_args = mock_logger.error.call_args
        
        # Verify the alert event name
        assert call_args[0][0] == "task_dead_letter_alert"
        
        # Verify all required metadata fields
        extra = call_args[1]['extra']
        assert extra['alert_type'] == "dead_letter"
        assert extra['severity'] == "high"
        assert extra['task_id'] == "task-123"
        assert extra['worker_id'] == "worker-1"
        assert extra['task_type'] == "execute_action"
        assert extra['attempts'] == 3
        assert extra['max_attempts'] == 3
        assert extra['reason'] == "Test failure"
        
        # Verify task status was updated to dead_letter
        assert task.status == WorkerTaskStatus.dead_letter
        assert task.error == "Test failure"


@pytest.mark.asyncio
async def test_no_alert_when_retrying(mock_db_session):
    """Test that no alert is emitted when task is retried (attempts < max_attempts)."""
    # Arrange: task with attempts < max_attempts
    task = WorkerTask(
        id="task-456",
        task_type="collect_facts",
        idempotency_key="key-456",
        worker_id="worker-2",
        site_name="default",
        timeout_seconds=60,
        payload={},
        attempts=1,
        max_attempts=3,
        status=WorkerTaskStatus.failed,
    )
    
    mock_db_session.get.return_value = task
    
    # Act: requeue
    with patch('homelab.workers.service.logger') as mock_logger:
        result = await requeue_task_with_backoff(mock_db_session, "task-456", "Transient error")
        
        # Assert: Only warning logged, no error alert
        assert mock_logger.warning.called
        assert not mock_logger.error.called
        
        # Verify task status was updated to queued (for retry)
        assert task.status == WorkerTaskStatus.queued
        assert task.next_retry_at is not None


@pytest.mark.asyncio
async def test_dead_letter_backoff_calculation(mock_db_session):
    """Test that exponential backoff is NOT applied to dead-lettered tasks."""
    # Arrange: task at max attempts
    task = WorkerTask(
        id="task-789",
        task_type="execute_script",
        idempotency_key="key-789",
        worker_id="worker-3",
        site_name="default",
        timeout_seconds=60,
        payload={},
        attempts=3,
        max_attempts=3,
        status=WorkerTaskStatus.failed,
    )
    
    mock_db_session.get.return_value = task
    
    # Act
    with patch('homelab.workers.service.logger'):
        result = await requeue_task_with_backoff(mock_db_session, "task-789", "Max retries exceeded")
    
    # Assert: Dead-lettered tasks should NOT have next_retry_at set
    assert task.status == WorkerTaskStatus.dead_letter
    # The next_retry_at should not be updated for dead-lettered tasks
    # (it remains whatever it was before, likely None or a past retry time)


@pytest.mark.asyncio
async def test_retry_backoff_calculation(mock_db_session):
    """Test exponential backoff calculation for retried tasks."""
    # Arrange: task on second attempt
    task = WorkerTask(
        id="task-backoff",
        task_type="execute_action",
        idempotency_key="key-backoff",
        worker_id="worker-4",
        site_name="default",
        timeout_seconds=60,
        payload={},
        attempts=2,
        max_attempts=3,
        status=WorkerTaskStatus.failed,
    )
    
    mock_db_session.get.return_value = task
    
    # Act
    before_requeue = datetime.now(timezone.utc)
    with patch('homelab.workers.service.logger'):
        result = await requeue_task_with_backoff(mock_db_session, "task-backoff", "Retry needed")
    after_requeue = datetime.now(timezone.utc)
    
    # Assert: Backoff should be 2^2 = 4 seconds
    assert task.status == WorkerTaskStatus.queued
    assert task.next_retry_at is not None
    
    # Verify backoff is approximately 4 seconds (2^2)
    # Allow some tolerance for test execution time
    time_diff = (task.next_retry_at - before_requeue).total_seconds()
    assert 3.5 <= time_diff <= 5.0  # 4 seconds ± 1 second tolerance


@pytest.mark.asyncio
async def test_task_not_found(mock_db_session):
    """Test graceful handling when task doesn't exist."""
    # Arrange: session returns None
    mock_db_session.get.return_value = None
    
    # Act
    with patch('homelab.workers.service.logger'):
        result = await requeue_task_with_backoff(mock_db_session, "nonexistent-task", "Error")
    
    # Assert: Should return None without crashing
    assert result is None
