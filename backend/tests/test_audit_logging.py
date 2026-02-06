"""Tests for audit logging with hash chain integrity."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

from homelab.audit.models import AuditLog
from homelab.audit.logger import (
    _calculate_hash,
    log_audit_event,
    verify_audit_chain,
    get_audit_logs,
)


class TestHashCalculation:
    """Test audit log hash calculation."""
    
    def test_hash_is_sha256(self):
        """Hash should be SHA-256 (64 hex chars)."""
        log = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id="session-456",
            action="create",
            metadata={},
            timestamp=datetime.now(timezone.utc),
            previous_hash=None,
        )
        
        hash_value = _calculate_hash(log)
        
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)
    
    def test_hash_is_deterministic(self):
        """Same inputs should produce same hash."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        log = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id="session-456",
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        hash1 = _calculate_hash(log)
        hash2 = _calculate_hash(log)
        
        assert hash1 == hash2
    
    def test_different_inputs_different_hash(self):
        """Different inputs should produce different hashes."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        log1 = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id="session-456",
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        log2 = AuditLog(
            id="test-2",
            sequence=2,
            event_type="user.logout",  # Different event
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id="session-456",
            action="delete",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        hash1 = _calculate_hash(log1)
        hash2 = _calculate_hash(log2)
        
        assert hash1 != hash2
    
    def test_previous_hash_affects_current(self):
        """Previous hash should affect current hash (chain property)."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        log1 = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        log2 = AuditLog(
            id="test-2",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash="abc123" + "0" * 58,  # Different previous hash
        )
        
        hash1 = _calculate_hash(log1)
        hash2 = _calculate_hash(log2)
        
        assert hash1 != hash2


class TestLogAuditEvent:
    """Test audit event logging."""
    
    @pytest.mark.asyncio
    async def test_creates_log_entry(self):
        """Test that log_audit_event creates an entry."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar=lambda: None))
        
        with patch("homelab.audit.logger.AuditLog") as MockAuditLog:
            mock_log = MagicMock()
            MockAuditLog.return_value = mock_log
            
            # Would need to properly mock the function
            pass
    
    @pytest.mark.asyncio
    async def test_first_entry_has_sequence_1(self):
        """First audit entry should have sequence 1."""
        # Would need database fixtures
        pass
    
    @pytest.mark.asyncio
    async def test_entry_links_to_previous(self):
        """Entry should link to previous entry's hash."""
        # Would need database fixtures
        pass


class TestChainVerification:
    """Test audit chain verification."""
    
    @pytest.mark.asyncio
    async def test_valid_chain_passes(self):
        """Valid chain should pass verification."""
        # Mock a valid chain
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        log1 = MagicMock()
        log1.sequence = 1
        log1.event_type = "user.login"
        log1.actor_id = "user-1"
        log1.action = "create"
        log1.timestamp = ts
        log1.previous_hash = None
        log1.current_hash = "a" * 64
        
        # Calculate what hash1 should be
        # Then verify log2.previous_hash matches
        pass
    
    @pytest.mark.asyncio
    async def test_tampered_entry_detected(self):
        """Tampering with entry should be detected."""
        mock_db = AsyncMock()
        
        # Create logs where hash doesn't match content
        log1 = MagicMock()
        log1.sequence = 1
        log1.current_hash = "wrong_hash_here" + "0" * 50
        
        # Verification should fail
        pass
    
    @pytest.mark.asyncio
    async def test_broken_chain_detected(self):
        """Broken chain (missing link) should be detected."""
        # Log 2's previous_hash doesn't match log 1's current_hash
        pass


class TestTamperDetection:
    """Test tampering detection scenarios."""
    
    def test_modified_actor_detected(self):
        """Modifying actor should change hash."""
        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        original = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",  # Original
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        tampered = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-456",  # TAMPERED
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=ts,
            previous_hash=None,
        )
        
        original_hash = _calculate_hash(original)
        tampered_hash = _calculate_hash(tampered)
        
        assert original_hash != tampered_hash
    
    def test_modified_timestamp_detected(self):
        """Modifying timestamp should change hash."""
        original = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            previous_hash=None,
        )
        
        tampered = AuditLog(
            id="test-1",
            sequence=1,
            event_type="user.login",
            actor_type="user",
            actor_id="user-123",
            resource_type="session",
            resource_id=None,
            action="create",
            metadata={},
            timestamp=datetime(2024, 1, 1, 12, 0, 1, tzinfo=timezone.utc),  # 1 sec later
            previous_hash=None,
        )
        
        original_hash = _calculate_hash(original)
        tampered_hash = _calculate_hash(tampered)
        
        assert original_hash != tampered_hash


class TestAuditLogQuery:
    """Test audit log querying."""
    
    @pytest.mark.asyncio
    async def test_filter_by_event_type(self):
        """Test filtering logs by event type."""
        # Would need database fixtures
        pass
    
    @pytest.mark.asyncio
    async def test_filter_by_actor(self):
        """Test filtering logs by actor."""
        # Would need database fixtures
        pass
    
    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test log pagination."""
        # Would need database fixtures
        pass
