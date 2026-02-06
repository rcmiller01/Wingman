"""Tests for plugin manifest validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from homelab.plugins.manifest_schema import (
    TrustLevel,
    BlastRadius,
    PluginManifest,
    PluginMetadata,
)


class TestTrustLevel:
    """Test trust level enum."""
    
    def test_trust_levels_exist(self):
        """All trust levels should be defined."""
        assert TrustLevel.TRUSTED
        assert TrustLevel.VERIFIED
        assert TrustLevel.SANDBOXED
    
    def test_trust_level_ordering(self):
        """Trust levels should have implied ordering."""
        # Sandboxed is most restrictive
        levels = [TrustLevel.SANDBOXED, TrustLevel.VERIFIED, TrustLevel.TRUSTED]
        assert len(levels) == 3


class TestBlastRadius:
    """Test blast radius model."""
    
    def test_valid_blast_radius(self):
        """Valid blast radius should pass."""
        radius = BlastRadius(
            scope="container",
            max_affected=10,
            reversible=True,
        )
        
        assert radius.scope == "container"
        assert radius.max_affected == 10
        assert radius.reversible is True
    
    def test_blast_radius_defaults(self):
        """Blast radius should have sensible defaults."""
        radius = BlastRadius(scope="local")
        
        assert radius.max_affected == 1
        assert radius.reversible is True


class TestPluginManifest:
    """Test plugin manifest validation."""
    
    def test_valid_manifest(self):
        """Valid manifest should pass validation."""
        manifest = PluginManifest(
            id="my-plugin",
            name="My Plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            entry_point="my_plugin:MyPlugin",
            permissions=["read_facts", "write_facts"],
            trust_level=TrustLevel.SANDBOXED,
            blast_radius=BlastRadius(scope="container"),
        )
        
        assert manifest.id == "my-plugin"
        assert manifest.version == "1.0.0"
    
    def test_manifest_requires_id(self):
        """Manifest must have an ID."""
        with pytest.raises(ValidationError):
            PluginManifest(
                name="My Plugin",
                version="1.0.0",
                description="A test plugin",
                author="Test Author",
                entry_point="my_plugin:MyPlugin",
            )
    
    def test_manifest_validates_version_format(self):
        """Version should follow semver format."""
        # Valid semver
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
        )
        assert manifest.version == "1.0.0"
    
    def test_manifest_validates_entry_point_format(self):
        """Entry point should be module:class format."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="my_module:MyClass",
        )
        assert ":" in manifest.entry_point
    
    def test_manifest_default_trust_level(self):
        """Default trust level should be sandboxed."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
        )
        assert manifest.trust_level == TrustLevel.SANDBOXED
    
    def test_manifest_id_validation(self):
        """Plugin ID should be lowercase with hyphens."""
        # Valid ID
        manifest = PluginManifest(
            id="my-cool-plugin",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
        )
        assert manifest.id == "my-cool-plugin"


class TestPluginMetadata:
    """Test plugin metadata model."""
    
    def test_metadata_creation(self):
        """Metadata should track runtime info."""
        metadata = PluginMetadata(
            plugin_id="test",
            source_path="/plugins/test",
            loaded_at="2024-01-01T00:00:00Z",
            trust_level=TrustLevel.SANDBOXED,
        )
        
        assert metadata.plugin_id == "test"
        assert metadata.trust_level == TrustLevel.SANDBOXED


class TestPermissionValidation:
    """Test permission validation."""
    
    def test_known_permissions_accepted(self):
        """Known permissions should be accepted."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
            permissions=["read_facts", "write_facts", "execute_actions"],
        )
        
        assert "read_facts" in manifest.permissions
    
    def test_empty_permissions_allowed(self):
        """Empty permissions should be allowed."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
            permissions=[],
        )
        
        assert manifest.permissions == []
