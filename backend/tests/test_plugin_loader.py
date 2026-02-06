"""Tests for plugin loader."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from homelab.plugins.loader import (
    load_manifest,
    load_plugin_class,
    discover_plugins,
    infer_trust_level,
)
from homelab.plugins.manifest_schema import TrustLevel


class TestLoadManifest:
    """Test manifest loading."""
    
    def test_load_valid_manifest(self, tmp_path):
        """Valid manifest.yaml should load successfully."""
        manifest_content = """
id: test-plugin
name: Test Plugin
version: 1.0.0
description: A test plugin
author: Test Author
entry_point: test_plugin:TestPlugin
permissions:
  - read_facts
"""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(manifest_content)
        
        manifest = load_manifest(tmp_path)
        
        assert manifest.id == "test-plugin"
        assert manifest.version == "1.0.0"
    
    def test_load_missing_manifest(self, tmp_path):
        """Missing manifest should raise error."""
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path)
    
    def test_load_invalid_yaml(self, tmp_path):
        """Invalid YAML should raise error."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("invalid: yaml: content: [")
        
        with pytest.raises(Exception):
            load_manifest(tmp_path)
    
    def test_load_manifest_with_blast_radius(self, tmp_path):
        """Manifest with blast radius should load."""
        manifest_content = """
id: test-plugin
name: Test Plugin
version: 1.0.0
description: A test plugin
author: Test Author
entry_point: test_plugin:TestPlugin
blast_radius:
  scope: container
  max_affected: 5
  reversible: true
"""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(manifest_content)
        
        manifest = load_manifest(tmp_path)
        
        assert manifest.blast_radius.scope == "container"
        assert manifest.blast_radius.max_affected == 5


class TestDiscoverPlugins:
    """Test plugin discovery."""
    
    def test_discover_plugins_in_directory(self, tmp_path):
        """Should find plugins with manifest.yaml."""
        # Create plugin directories
        plugin1 = tmp_path / "plugin1"
        plugin1.mkdir()
        (plugin1 / "manifest.yaml").write_text("""
id: plugin1
name: Plugin 1
version: 1.0.0
description: First plugin
author: Test
entry_point: plugin1:Plugin1
""")
        
        plugin2 = tmp_path / "plugin2"
        plugin2.mkdir()
        (plugin2 / "manifest.yaml").write_text("""
id: plugin2
name: Plugin 2
version: 1.0.0
description: Second plugin
author: Test
entry_point: plugin2:Plugin2
""")
        
        plugins = discover_plugins(tmp_path)
        
        assert len(plugins) == 2
        plugin_ids = [p.id for p in plugins]
        assert "plugin1" in plugin_ids
        assert "plugin2" in plugin_ids
    
    def test_discover_ignores_non_plugin_dirs(self, tmp_path):
        """Should ignore directories without manifest.yaml."""
        # Create non-plugin directory
        not_plugin = tmp_path / "not_a_plugin"
        not_plugin.mkdir()
        (not_plugin / "some_file.txt").write_text("not a manifest")
        
        plugins = discover_plugins(tmp_path)
        
        assert len(plugins) == 0
    
    def test_discover_empty_directory(self, tmp_path):
        """Empty directory should return empty list."""
        plugins = discover_plugins(tmp_path)
        
        assert plugins == []


class TestInferTrustLevel:
    """Test trust level inference."""
    
    def test_builtin_plugins_trusted(self):
        """Built-in plugins should be trusted."""
        # Plugins in the application directory
        trust = infer_trust_level(Path("/app/homelab/plugins/builtin"))
        
        assert trust == TrustLevel.TRUSTED
    
    def test_user_plugins_sandboxed(self):
        """User-installed plugins should be sandboxed."""
        trust = infer_trust_level(Path("/home/user/.wingman/plugins/custom"))
        
        assert trust == TrustLevel.SANDBOXED
    
    def test_verified_plugins_directory(self):
        """Verified plugins directory should use VERIFIED level."""
        trust = infer_trust_level(Path("/app/plugins/verified/some-plugin"))
        
        assert trust == TrustLevel.VERIFIED


class TestLoadPluginClass:
    """Test plugin class loading."""
    
    def test_load_valid_plugin_class(self):
        """Valid entry point should load class."""
        # This would need a real plugin module
        # For now, test the concept
        pass
    
    def test_load_missing_module(self):
        """Missing module should raise ImportError."""
        with pytest.raises(ImportError):
            load_plugin_class("nonexistent_module:SomeClass")
    
    def test_load_missing_class(self):
        """Missing class in module should raise AttributeError."""
        # Would need mock module
        pass
