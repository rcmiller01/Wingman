"""Dataclasses for execution plugin request/response payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class PluginAction:
    """Normalized action envelope passed to execution plugins."""

    action: str
    target: str
    params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PluginExecutionResult:
    """Normalized result envelope returned by execution plugins."""

    success: bool
    plugin_id: str
    action: str
    target: str
    started_at: datetime
    completed_at: datetime
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this result to a JSON-safe dictionary."""

        return {
            "success": self.success,
            "plugin_id": self.plugin_id,
            "action": self.action,
            "target": self.target,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
        }
