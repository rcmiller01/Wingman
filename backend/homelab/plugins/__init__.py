"""Plugins package."""

from homelab.plugins.manifest_schema import (
    TrustLevel,
    BlastRadius,
    PluginManifest,
    PluginMetadata,
)
from homelab.plugins.loader import (
    PluginLoadError,
    load_manifest,
    load_plugin,
    discover_plugins,
    infer_trust_level,
)
from homelab.plugins.sandbox import run_sandboxed

__all__ = [
    # Manifest schema
    "TrustLevel",
    "BlastRadius",
    "PluginManifest",
    "PluginMetadata",
    
    # Loader
    "PluginLoadError",
    "load_manifest",
    "load_plugin",
    "discover_plugins",
    "infer_trust_level",
    
    # Sandbox
    "run_sandboxed",
]
