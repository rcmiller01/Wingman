"""Registry for execution plugins."""

from __future__ import annotations

from collections.abc import Iterable

from .base import ExecutionPlugin
from .errors import DuplicatePluginError, PluginNotFoundError


class PluginRegistry:
    """In-memory registry for execution plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, ExecutionPlugin] = {}

    def register(self, plugin: ExecutionPlugin) -> None:
        """Register a plugin by its ``plugin_id``.

        Raises:
            DuplicatePluginError: If plugin_id already exists.
        """

        plugin_id = plugin.plugin_id.strip()
        if not plugin_id:
            raise ValueError("Plugin ID cannot be empty")
        if plugin_id in self._plugins:
            raise DuplicatePluginError(f"Plugin already registered: {plugin_id}")
        self._plugins[plugin_id] = plugin

    def register_many(self, plugins: Iterable[ExecutionPlugin]) -> None:
        """Register multiple plugins."""

        for plugin in plugins:
            self.register(plugin)

    def get(self, plugin_id: str) -> ExecutionPlugin:
        """Get a plugin by identifier.

        Raises:
            PluginNotFoundError: If plugin does not exist.
        """

        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginNotFoundError(f"Plugin not found: {plugin_id}") from exc

    def get_for_action(self, action: str) -> ExecutionPlugin:
        """Resolve a plugin supporting the provided action.

        Raises:
            PluginNotFoundError: If no plugin supports ``action``.
        """

        for plugin in self._plugins.values():
            if action in plugin.supported_actions:
                return plugin
        raise PluginNotFoundError(f"No plugin supports action: {action}")

    def list_ids(self) -> list[str]:
        """List all registered plugin ids."""

        return sorted(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins (test utility)."""

        self._plugins.clear()
