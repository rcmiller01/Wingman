"""Enhanced plugin registry with trust level enforcement."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Type

from homelab.execution_plugins.registry import PluginRegistry
from homelab.execution_plugins.base import ExecutionPlugin
from homelab.plugins.manifest_schema import TrustLevel, PluginManifest, PluginMetadata
from homelab.plugins.loader import discover_plugins, PluginLoadError


logger = logging.getLogger(__name__)


class EnhancedPluginRegistry(PluginRegistry):
    """Plugin registry with trust level enforcement and metadata tracking."""
    
    def __init__(self):
        super().__init__()
        self.manifests: dict[str, PluginManifest] = {}
        self.metadata: dict[str, PluginMetadata] = {}
    
    def register_with_manifest(
        self,
        plugin: ExecutionPlugin,
        manifest: PluginManifest,
        plugin_dir: Path,
        signature_verified: bool = False,
    ):
        """Register plugin with manifest and metadata.
        
        Args:
            plugin: Plugin instance
            manifest: Plugin manifest
            plugin_dir: Plugin directory path
            signature_verified: Whether signature was verified
        """
        from datetime import datetime, timezone
        
        # Register plugin with base registry
        self.register(plugin)
        
        # Store manifest
        self.manifests[plugin.plugin_id] = manifest
        
        # Store metadata
        self.metadata[plugin.plugin_id] = PluginMetadata(
            manifest=manifest,
            plugin_dir=str(plugin_dir),
            loaded_at=datetime.now(timezone.utc).isoformat(),
            signature_verified=signature_verified,
        )
        
        logger.info(
            f"Registered plugin: {manifest.id} v{manifest.version} "
            f"(trust_level={manifest.trust_level.value}, "
            f"verified={signature_verified})"
        )
    
    def get_trust_level(self, plugin_id: str) -> TrustLevel:
        """Get trust level for plugin.
        
        Args:
            plugin_id: Plugin ID
        
        Returns:
            Trust level (defaults to SANDBOXED if not found)
        """
        manifest = self.manifests.get(plugin_id)
        return manifest.trust_level if manifest else TrustLevel.SANDBOXED
    
    def get_manifest(self, plugin_id: str) -> PluginManifest | None:
        """Get manifest for plugin.
        
        Args:
            plugin_id: Plugin ID
        
        Returns:
            Plugin manifest or None if not found
        """
        return self.manifests.get(plugin_id)
    
    def get_metadata(self, plugin_id: str) -> PluginMetadata | None:
        """Get metadata for plugin.
        
        Args:
            plugin_id: Plugin ID
        
        Returns:
            Plugin metadata or None if not found
        """
        return self.metadata.get(plugin_id)
    
    def list_plugins_by_trust_level(self, trust_level: TrustLevel) -> list[str]:
        """List all plugins with specified trust level.
        
        Args:
            trust_level: Trust level to filter by
        
        Returns:
            List of plugin IDs
        """
        return [
            plugin_id
            for plugin_id, manifest in self.manifests.items()
            if manifest.trust_level == trust_level
        ]
    
    def load_all_plugins(self, plugins_dir: Path):
        """Discover and load all plugins from directory.
        
        Args:
            plugins_dir: Base plugins directory
        """
        logger.info(f"Loading plugins from {plugins_dir}")
        
        plugins = discover_plugins(plugins_dir)
        
        for manifest, plugin_class in plugins:
            try:
                # Instantiate plugin
                plugin_instance = plugin_class()
                
                # Determine plugin directory
                # This is a bit hacky - we need to track this during discovery
                plugin_dir = plugins_dir / manifest.id
                
                # Register with manifest
                self.register_with_manifest(
                    plugin_instance,
                    manifest,
                    plugin_dir,
                    signature_verified=False,  # TODO: Implement signature verification
                )
            
            except Exception as e:
                logger.error(f"Failed to instantiate plugin {manifest.id}: {e}")
        
        logger.info(f"Loaded {len(self.manifests)} plugins")
    
    def get_plugin_summary(self) -> dict[str, int]:
        """Get summary of loaded plugins by trust level.
        
        Returns:
            Dict mapping trust level to count
        """
        summary = {
            TrustLevel.TRUSTED.value: 0,
            TrustLevel.VERIFIED.value: 0,
            TrustLevel.SANDBOXED.value: 0,
        }
        
        for manifest in self.manifests.values():
            summary[manifest.trust_level.value] += 1
        
        return summary


# Global enhanced registry instance
enhanced_registry = EnhancedPluginRegistry()
