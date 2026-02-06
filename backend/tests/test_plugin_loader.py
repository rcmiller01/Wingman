"""Tests for plugin loader."""

from __future__ import annotations

import pytest
from pathlib import Path

from homelab.plugins.manifest_schema import TrustLevel
from homelab.plugins.loader import (
    load_manifest,
    discover_plugins,
    infer_trust_level,
    PluginLoadError,
)


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
blast_radius:
  scope: container
  mutates_state: false
  reversible: true
permissions:
  - docker:read
"""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(manifest_content)
        
        manifest = load_manifest(tmp_path)
        
        assert manifest.id == "test-plugin"
        assert manifest.version == "1.0.0"
    
    def test_load_missing_manifest(self, tmp_path):
        """Missing manifest should raise error."""
        with pytest.raises((FileNotFoundError, PluginLoadError)):
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
  mutates_state: true
  reversible: true
"""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(manifest_content)
        
        manifest = load_manifest(tmp_path)
        
        assert manifest.blast_radius.scope == "container"
        assert manifest.blast_radius.mutates_state is True


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
blast_radius:
  scope: local
  mutates_state: false
  reversible: true
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
blast_radius:
  scope: local
  mutates_state: false
  reversible: true
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
    
    def test_returns_trust_level(self):
        """Should return a TrustLevel."""
        trust = infer_trust_level(Path("/some/path"))
        
        assert isinstance(trust, TrustLevel)
