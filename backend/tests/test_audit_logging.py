"""Tests for audit logging concepts (hash chain integrity)."""

from __future__ import annotations

import hashlib
import pytest


class TestHashChainConcepts:
    """Test hash chain concepts (without database)."""
    
    def test_sha256_produces_64_chars(self):
        """SHA-256 hash should produce 64 hex chars."""
        data = "test data"
        hash_value = hashlib.sha256(data.encode()).hexdigest()
        
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)
    
    def test_hash_is_deterministic(self):
        """Same input should produce same hash."""
        data = "test data"
        hash1 = hashlib.sha256(data.encode()).hexdigest()
        hash2 = hashlib.sha256(data.encode()).hexdigest()
        
        assert hash1 == hash2
    
    def test_different_inputs_different_hash(self):
        """Different inputs should produce different hashes."""
        data1 = "test data 1"
        data2 = "test data 2"
        hash1 = hashlib.sha256(data1.encode()).hexdigest()
        hash2 = hashlib.sha256(data2.encode()).hexdigest()
        
        assert hash1 != hash2
    
    def test_chain_depends_on_previous(self):
        """Chain hash includes previous hash."""
        prev_hash = "a" * 64
        data_with_prev = f"1:event:actor:action:2024-01-01T00:00:00+00:00:{prev_hash}"
        data_without = "1:event:actor:action:2024-01-01T00:00:00+00:00:"
        
        hash_with_prev = hashlib.sha256(data_with_prev.encode()).hexdigest()
        hash_without = hashlib.sha256(data_without.encode()).hexdigest()
        
        assert hash_with_prev != hash_without


class TestTamperDetectionConcepts:
    """Test tamper detection concepts."""
    
    def test_modified_data_changes_hash(self):
        """Modifying any field should change the hash."""
        original = "1:user.login:user-123:create:2024-01-01T00:00:00+00:00:"
        tampered = "1:user.login:user-456:create:2024-01-01T00:00:00+00:00:"
        
        original_hash = hashlib.sha256(original.encode()).hexdigest()
        tampered_hash = hashlib.sha256(tampered.encode()).hexdigest()
        
        assert original_hash != tampered_hash
    
    def test_modified_timestamp_changes_hash(self):
        """Modifying timestamp should change the hash."""
        original = "1:user.login:user-123:create:2024-01-01T00:00:00+00:00:"
        tampered = "1:user.login:user-123:create:2024-01-01T00:00:01+00:00:"
        
        original_hash = hashlib.sha256(original.encode()).hexdigest()
        tampered_hash = hashlib.sha256(tampered.encode()).hexdigest()
        
        assert original_hash != tampered_hash
    
    def test_broken_chain_detectable(self):
        """Breaking chain link is detectable."""
        # Entry 1
        entry1 = "1:login:user-1:create:2024-01-01T00:00:00+00:00:"
        entry1_hash = hashlib.sha256(entry1.encode()).hexdigest()
        
        # Entry 2 with correct previous_hash
        entry2_valid = f"2:logout:user-1:create:2024-01-01T01:00:00+00:00:{entry1_hash}"
        entry2_valid_hash = hashlib.sha256(entry2_valid.encode()).hexdigest()
        
        # Entry 2 with tampered previous_hash
        wrong_prev = "b" * 64
        entry2_tampered = f"2:logout:user-1:create:2024-01-01T01:00:00+00:00:{wrong_prev}"
        entry2_tampered_hash = hashlib.sha256(entry2_tampered.encode()).hexdigest()
        
        # Hashes are different - tampering detectable
        assert entry2_valid_hash != entry2_tampered_hash


class TestChainIntegrity:
    """Test chain integrity properties."""
    
    def test_chain_produces_unique_hashes(self):
        """Each entry in a chain has unique hash."""
        hashes = []
        prev_hash = ""
        
        for i in range(5):
            entry = f"{i}:event:actor:action:2024-01-01T00:00:0{i}+00:00:{prev_hash}"
            current_hash = hashlib.sha256(entry.encode()).hexdigest()
            hashes.append(current_hash)
            prev_hash = current_hash
        
        # All hashes should be unique
        assert len(set(hashes)) == 5
    
    def test_first_entry_has_empty_previous(self):
        """First entry has no previous hash."""
        entry1 = "1:event:actor:action:2024-01-01T00:00:00+00:00:"
        hash1 = hashlib.sha256(entry1.encode()).hexdigest()
        
        # Should produce a valid hash even without previous
        assert len(hash1) == 64
    
    def test_chain_order_matters(self):
        """Changing sequence number changes hash."""
        entry_seq1 = "1:event:actor:action:2024-01-01T00:00:00+00:00:"
        entry_seq2 = "2:event:actor:action:2024-01-01T00:00:00+00:00:"
        
        hash1 = hashlib.sha256(entry_seq1.encode()).hexdigest()
        hash2 = hashlib.sha256(entry_seq2.encode()).hexdigest()
        
        assert hash1 != hash2
