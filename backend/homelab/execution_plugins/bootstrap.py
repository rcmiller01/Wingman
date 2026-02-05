"""Bootstrap helpers for built-in execution plugin registration."""

from __future__ import annotations

from .docker_plugin import DockerPlugin
from .script_plugin import ScriptPlugin
from .registry import PluginRegistry


def build_default_registry() -> PluginRegistry:
    """Build a registry populated with built-in execution plugins."""

    registry = PluginRegistry()
    registry.register(DockerPlugin())
    registry.register(ScriptPlugin())
    return registry


execution_registry = build_default_registry()
