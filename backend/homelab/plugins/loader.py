"""Plugin loading and validation."""

from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Type

import yaml
from pydantic import ValidationError

from homelab.plugins.manifest_schema import PluginManifest, PluginMetadata, TrustLevel
from homelab.execution_plugins.base import ExecutionPlugin


logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Plugin loading failed."""
    pass


def load_manifest(plugin_dir: Path) -> PluginManifest:
    """Load and validate plugin manifest.
    
    Args:
        plugin_dir: Directory containing manifest.yaml
    
    Returns:
        Validated plugin manifest
    
    Raises:
        PluginLoadError: If manifest is missing or invalid
    """
    manifest_path = plugin_dir / "manifest.yaml"
    
    if not manifest_path.exists():
        raise PluginLoadError(f"No manifest.yaml found in {plugin_dir}")
    
    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise PluginLoadError(f"Invalid YAML in manifest: {e}")
    
    try:
        return PluginManifest(**data)
    except ValidationError as e:
        raise PluginLoadError(f"Invalid manifest: {e}")


def load_plugin_class(
    plugin_dir: Path,
    manifest: PluginManifest
) -> Type[ExecutionPlugin]:
    """Load plugin class from entry point.
    
    Args:
        plugin_dir: Directory containing plugin code
        manifest: Plugin manifest
    
    Returns:
        Plugin class (not instantiated)
    
    Raises:
        PluginLoadError: If plugin cannot be loaded
    """
    # Parse entry point
    try:
        module_path, class_name = manifest.entry_point.split(":")
    except ValueError:
        raise PluginLoadError(f"Invalid entry point format: {manifest.entry_point}")
    
    # Find plugin file
    plugin_file = plugin_dir / f"{module_path}.py"
    
    if not plugin_file.exists():
        raise PluginLoadError(f"Entry point file not found: {plugin_file}")
    
    # Load module
    module_name = f"plugin_{manifest.id.replace('-', '_')}"
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Failed to create module spec for {plugin_file}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        raise PluginLoadError(f"Failed to load module {plugin_file}: {e}")
    
    # Get plugin class
    if not hasattr(module, class_name):
        raise PluginLoadError(f"Class {class_name} not found in {plugin_file}")
    
    plugin_class = getattr(module, class_name)
    
    # Validate plugin class
    if not isinstance(plugin_class, type):
        raise PluginLoadError(f"{class_name} is not a class")
    
    if not issubclass(plugin_class, ExecutionPlugin):
        raise PluginLoadError(f"{class_name} must inherit from ExecutionPlugin")
    
    return plugin_class


def load_plugin(plugin_dir: Path) -> tuple[PluginManifest, Type[ExecutionPlugin]]:
    """Load plugin from directory.
    
    Args:
        plugin_dir: Directory containing manifest.yaml and plugin code
    
    Returns:
        (manifest, plugin_class)
    
    Raises:
        PluginLoadError: If plugin cannot be loaded
    """
    manifest = load_manifest(plugin_dir)
    plugin_class = load_plugin_class(plugin_dir, manifest)
    
    logger.info(
        f"Loaded plugin: {manifest.id} v{manifest.version} "
        f"(trust_level={manifest.trust_level.value})"
    )
    
    return manifest, plugin_class


def discover_plugins(base_dir: Path) -> list[tuple[PluginManifest, Type[ExecutionPlugin]]]:
    """Discover all plugins in directory structure.
    
    Expected structure:
        plugins/
        ├── core/           # Built-in (trusted)
        │   └── docker-plugin/
        │       ├── manifest.yaml
        │       └── plugin.py
        ├── community/      # Downloaded from marketplace
        │   └── proxmox-snapshot/
        │       ├── manifest.yaml
        │       └── plugin.py
        └── local/          # User's private plugins
            └── custom-plugin/
                ├── manifest.yaml
                └── plugin.py
    
    Args:
        base_dir: Base directory to search for plugins
    
    Returns:
        List of (manifest, plugin_class) tuples
    """
    plugins = []
    
    if not base_dir.exists():
        logger.warning(f"Plugin directory does not exist: {base_dir}")
        return plugins
    
    # Search for manifest.yaml files
    for manifest_path in base_dir.rglob("manifest.yaml"):
        plugin_dir = manifest_path.parent
        
        try:
            manifest, plugin_class = load_plugin(plugin_dir)
            plugins.append((manifest, plugin_class))
        except PluginLoadError as e:
            logger.warning(f"Failed to load plugin from {plugin_dir}: {e}")
    
    logger.info(f"Discovered {len(plugins)} plugins in {base_dir}")
    return plugins


def infer_trust_level(plugin_dir: Path, base_dir: Path) -> TrustLevel:
    """Infer trust level based on plugin location.
    
    Args:
        plugin_dir: Plugin directory
        base_dir: Base plugins directory
    
    Returns:
        Inferred trust level
    """
    try:
        relative_path = plugin_dir.relative_to(base_dir)
        parts = relative_path.parts
        
        if len(parts) > 0:
            category = parts[0]
            
            if category == "core":
                return TrustLevel.TRUSTED
            elif category == "verified":
                return TrustLevel.VERIFIED
            elif category in ("community", "local"):
                return TrustLevel.SANDBOXED
    except ValueError:
        pass
    
    # Default to sandboxed
    return TrustLevel.SANDBOXED
