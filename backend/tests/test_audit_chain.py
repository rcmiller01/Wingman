"""
Tests for audit hash chain integrity.

Verifies:
- Hash chain computation is deterministic
- Tampering is detectable via hash changes
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from homelab.storage.audit_chain import (
    GENESIS_HASH,
    compute_entry_hash,
    get_chain_head,
    prepare_chained_entry,
)
from homelab.storage.models import ActionHistory, ActionTemplate, ActionStatus


class TestHashComputation:
    """Test deterministic hash computation."""
    
    def test_genesis_hash_is_64_zeros(self):
        """Genesis hash should be 64 hex zeros."""
        assert GENESIS_HASH == "0" * 64
        assert len(GENESIS_HASH) == 64
    
    def test_compute_entry_hash_deterministic(self):
        """Same inputs should produce same hash."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"ok": True},
        )
        
        hash2 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"ok": True},
        )
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest
    
    def test_compute_entry_hash_different_target_different_hash(self):
        """Different inputs should produce different hashes."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"ok": True},
        )
        
        # Different target
        hash2 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:redis",
            requested_at=ts,
            result={"ok": True},
        )
        
        assert hash1 != hash2
    
    def test_prev_hash_affects_entry_hash(self):
        """Changing prev_hash should change entry_hash (chain property)."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"ok": True},
        )
        
        hash2 = compute_entry_hash(
            prev_hash="a" * 64,  # Different prev_hash
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"ok": True},
        )
        
        assert hash1 != hash2


class TestChainOperations:
    """Test chain head retrieval and entry preparation."""
    
    @pytest.mark.asyncio
    async def test_get_chain_head_empty_returns_genesis(self):
        """Empty chain should return genesis hash with seq 1."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None  # Empty chain
        mock_db.execute.return_value = mock_result
        
        prev_hash, seq_num = await get_chain_head(mock_db)
        
        assert prev_hash == GENESIS_HASH
        assert seq_num == 1  # First entry gets seq 1
    
    @pytest.mark.asyncio
    async def test_get_chain_head_with_entries(self):
        """Should return next sequence and last hash."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        # first() returns a Row-like object with entry_hash and sequence_num
        mock_row = MagicMock()
        mock_row.entry_hash = "abc123" + "0" * 58  # 64 chars
        mock_row.sequence_num = 5
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result
        
        prev_hash, seq_num = await get_chain_head(mock_db)
        
        assert prev_hash == mock_row.entry_hash
        assert seq_num == 6  # Next sequence
    
    @pytest.mark.asyncio
    async def test_prepare_chained_entry_first_entry(self):
        """First entry should link to genesis."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None  # Empty chain
        mock_db.execute.return_value = mock_result
        
        action = ActionHistory(
            action_template=ActionTemplate.restart_resource,
            target_resource="container:nginx",
            status=ActionStatus.completed,
            requested_at=datetime.now(timezone.utc),
            result={"success": True},
        )
        
        await prepare_chained_entry(mock_db, action)
        
        assert action.prev_hash == GENESIS_HASH
        assert action.sequence_num == 1
        assert action.entry_hash is not None
        assert len(action.entry_hash) == 64
    
    @pytest.mark.asyncio
    async def test_prepare_chained_entry_subsequent_entry(self):
        """Subsequent entries should link to previous."""
        mock_db = AsyncMock()
        
        # Simulate existing chain head
        mock_row = MagicMock()
        mock_row.entry_hash = "f" * 64
        mock_row.sequence_num = 10
        
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result
        
        action = ActionHistory(
            action_template=ActionTemplate.stop_resource,
            target_resource="vm:dev-server",
            status=ActionStatus.completed,
            requested_at=datetime.now(timezone.utc),
            result={"stopped": True},
        )
        
        await prepare_chained_entry(mock_db, action)
        
        assert action.prev_hash == "f" * 64
        assert action.sequence_num == 11
        assert action.entry_hash is not None
        assert action.entry_hash != action.prev_hash


class TestSecurityProperties:
    """Test security properties of the hash chain."""
    
    def test_result_changes_affect_hash(self):
        """Modifying result should invalidate entry hash."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        original_result = {"status": "success", "data": "original"}
        tampered_result = {"status": "success", "data": "tampered"}
        
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result=original_result,
        )
        
        hash2 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result=tampered_result,
        )
        
        assert hash1 != hash2, "Tampering with result should change hash"
    
    def test_timestamp_changes_affect_hash(self):
        """Modifying timestamp should invalidate entry hash."""
        ts1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc)  # 1 second later
        
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts1,
        )
        
        hash2 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts2,
        )
        
        assert hash1 != hash2, "Tampering with timestamp should change hash"
    
    def test_chain_property_cascading_invalidation(self):
        """Modifying early entry should invalidate all subsequent hashes."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Build a 3-entry chain
        hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"op": "result1"},
        )
        
        hash2 = compute_entry_hash(
            prev_hash=hash1,
            action_template="stop_resource",
            target_resource="container:redis",
            requested_at=ts,
            result={"op": "result2"},
        )
        
        # Now tamper with entry 1
        tampered_hash1 = compute_entry_hash(
            prev_hash=GENESIS_HASH,
            action_template="restart_resource",
            target_resource="container:nginx",
            requested_at=ts,
            result={"op": "TAMPERED"},
        )
        
        # Since hash1 != tampered_hash1, any chain built on tampered_hash1
        # would have different hashes
        assert hash1 != tampered_hash1, "Tampered entry should have different hash"
        
        # Entry 2's hash would be different if based on tampered entry 1
        new_hash2 = compute_entry_hash(
            prev_hash=tampered_hash1,
            action_template="stop_resource",
            target_resource="container:redis",
            requested_at=ts,
            result={"op": "result2"},
        )
        
        assert hash2 != new_hash2, "Tampering should cascade - entry 2 hash changes"
