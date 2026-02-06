"""Bootstrap helpers for built-in execution plugin registration."""

from __future__ import annotations

import logging
from pathlib import Path

from .script_plugin import ScriptPlugin
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


def build_default_registry() -> PluginRegistry:
    """Build a registry populated with built-in execution plugins.
    
    Note: This returns the base PluginRegistry for backward compatibility.
    For enhanced plugin support with trust levels and marketplace,
    use homelab.plugins.registry.enhanced_registry instead.
    """

    registry = PluginRegistry()
    registry.register(ScriptPlugin())
    
    # Lazy-load Docker plugin to avoid import-time failures
    # when Docker SDK is unavailable (e.g., in environments without Docker)
    try:
        from .docker_plugin import DockerPlugin
        registry.register(DockerPlugin())
    except ImportError as e:
        logger.warning(
            "docker_plugin_unavailable",
            extra={
                "reason": str(e),
                "message": "Docker plugin will not be available. Install docker package to enable Docker support."
            },
        )
    
    return registry


def build_enhanced_registry(plugins_dir: Path | None = None):
    """Build enhanced registry with plugin marketplace support.
    
    Args:
        plugins_dir: Optional plugins directory to load from.
                     If None, only built-in plugins are loaded.
    
    Returns:
        EnhancedPluginRegistry instance
    """
    from homelab.plugins.registry import EnhancedPluginRegistry
    from homelab.plugins.manifest_schema import TrustLevel, PluginManifest, BlastRadius
    
    registry = EnhancedPluginRegistry()
    
    # Register built-in script plugin
    script_plugin = ScriptPlugin()
    script_manifest = PluginManifest(
        id="script",
        name="Script Execution Plugin",
        version="1.0.0",
        author="wingman-core",
        description="Execute bash and Python scripts",
        trust_level=TrustLevel.TRUSTED,
        permissions=["script:execute"],
        blast_radius=BlastRadius(
            scope="host",
            mutates_state=True,
            reversible=False,
        ),
        entry_point="script_plugin:ScriptPlugin",
    )
    registry.register_with_manifest(
        script_plugin,
        script_manifest,
        Path(__file__).parent,
        signature_verified=True,
    )
    
    # Register Docker plugin if available
    try:
        from .docker_plugin import DockerPlugin
        
        docker_plugin = DockerPlugin()
        docker_manifest = PluginManifest(
            id="docker",
            name="Docker Plugin",
            version="1.0.0",
            author="wingman-core",
            description="Manage Docker containers",
            trust_level=TrustLevel.TRUSTED,
            permissions=["docker:read", "docker:write", "docker:execute"],
            blast_radius=BlastRadius(
                scope="container",
                mutates_state=True,
                reversible=True,
            ),
            entry_point="docker_plugin:DockerPlugin",
        )
        registry.register_with_manifest(
            docker_plugin,
            docker_manifest,
            Path(__file__).parent,
            signature_verified=True,
        )
    except ImportError as e:
        logger.warning(
            "docker_plugin_unavailable",
            extra={
                "reason": str(e),
                "message": "Docker plugin will not be available."
            },
        )
    
    # Load additional plugins from directory if provided
    if plugins_dir and plugins_dir.exists():
        logger.info(f"Loading plugins from {plugins_dir}")
        registry.load_all_plugins(plugins_dir)
    
    return registry


# Default registry (backward compatibility)
execution_registry = build_default_registry()

