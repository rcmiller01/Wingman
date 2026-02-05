"""Base contract for execution plugins.

All execution plugins must implement this interface.

Lifecycle:
1) ``validate_pre`` checks action suitability and returns ``(ok, message)``.
2) ``execute`` performs the requested action and returns a result payload.
3) ``validate_post`` checks postconditions and returns ``(ok, message)``.
4) ``rollback`` best-effort rollback when supported.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import PluginAction


class ExecutionPlugin(ABC):
    """Abstract execution plugin contract."""

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Stable unique plugin identifier."""

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """Action names this plugin can execute."""

    @abstractmethod
    async def validate_pre(self, action: PluginAction) -> tuple[bool, str]:
        """Validate preconditions before execution."""

    @abstractmethod
    async def execute(self, action: PluginAction) -> dict[str, Any]:
        """Execute an action and return a result payload."""

    @abstractmethod
    async def validate_post(self, action: PluginAction, result: dict[str, Any]) -> tuple[bool, str]:
        """Validate postconditions after execution."""

    @abstractmethod
    async def rollback(self, action: PluginAction, result: dict[str, Any]) -> bool:
        """Best-effort rollback after failed or invalid execution."""
