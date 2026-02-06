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
    
    def test_trust_level_count(self):
        """Should have expected trust levels."""
        assert len(TrustLevel) >= 3


class TestBlastRadius:
    """Test blast radius model."""
    
    def test_valid_blast_radius(self):
        """Valid blast radius should pass."""
        radius = BlastRadius(
            scope="container",
            mutates_state=True,
            reversible=True,
        )
        
        assert radius.scope == "container"
        assert radius.mutates_state is True
        assert radius.reversible is True
    
    def test_blast_radius_fields(self):
        """Blast radius should have required fields."""
        radius = BlastRadius(scope="local", mutates_state=False, reversible=True)
        
        assert hasattr(radius, 'scope')
        assert hasattr(radius, 'mutates_state')
        assert hasattr(radius, 'reversible')


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
            permissions=["docker:read"],
            trust_level=TrustLevel.SANDBOXED,
            blast_radius=BlastRadius(scope="container", mutates_state=False, reversible=True),
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
                blast_radius=BlastRadius(scope="local", mutates_state=False, reversible=True),
            )
    
    def test_manifest_has_expected_fields(self):
        """Manifest should have expected fields."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
            blast_radius=BlastRadius(scope="local", mutates_state=False, reversible=True),
        )
        
        assert hasattr(manifest, 'id')
        assert hasattr(manifest, 'name')
        assert hasattr(manifest, 'version')
        assert hasattr(manifest, 'entry_point')


class TestPluginMetadata:
    """Test plugin metadata model."""
    
    def test_metadata_fields(self):
        """Metadata should have expected fields."""
        assert hasattr(PluginMetadata, 'model_fields')


class TestPermissionValidation:
    """Test permission validation."""
    
    def test_permissions_list(self):
        """Permissions should be a list."""
        manifest = PluginManifest(
            id="test",
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:Test",
            permissions=["docker:read", "proxmox:read"],
            blast_radius=BlastRadius(scope="local", mutates_state=False, reversible=True),
        )
        
        assert isinstance(manifest.permissions, list)
    
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
            blast_radius=BlastRadius(scope="local", mutates_state=False, reversible=True),
        )
        
        assert manifest.permissions == []
