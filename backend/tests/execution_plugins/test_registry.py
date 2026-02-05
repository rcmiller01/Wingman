from __future__ import annotations

from datetime import datetime, timezone

import pytest

from homelab.execution_plugins import (
    DuplicatePluginError,
    ExecutionPlugin,
    PluginAction,
    PluginNotFoundError,
    PluginRegistry,
)


class DummyPlugin(ExecutionPlugin):
    def __init__(self, plugin_id: str, actions: list[str]):
        self._plugin_id = plugin_id
        self._actions = actions

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def supported_actions(self) -> list[str]:
        return self._actions

    async def validate_pre(self, action: PluginAction) -> tuple[bool, str]:
        return True, "ok"

    async def execute(self, action: PluginAction) -> dict:
        return {
            "success": True,
            "plugin_id": self.plugin_id,
            "action": action.action,
            "target": action.target,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "data": {},
            "error": None,
            "error_code": None,
        }

    async def validate_post(self, action: PluginAction, result: dict) -> tuple[bool, str]:
        return True, "ok"

    async def rollback(self, action: PluginAction, result: dict) -> bool:
        return False


def test_register_and_get_plugin():
    registry = PluginRegistry()
    plugin = DummyPlugin("docker", ["restart", "stop"])

    registry.register(plugin)

    resolved = registry.get("docker")
    assert resolved is plugin


def test_register_duplicate_plugin_raises():
    registry = PluginRegistry()
    registry.register(DummyPlugin("docker", ["restart"]))

    with pytest.raises(DuplicatePluginError, match="already registered"):
        registry.register(DummyPlugin("docker", ["stop"]))


def test_get_unknown_plugin_raises_not_found():
    registry = PluginRegistry()

    with pytest.raises(PluginNotFoundError, match="Plugin not found"):
        registry.get("missing")


def test_get_for_action_returns_first_matching_plugin():
    registry = PluginRegistry()
    docker = DummyPlugin("docker", ["restart", "stop"])
    script = DummyPlugin("script", ["run_bash"])
    registry.register_many([docker, script])

    resolved = registry.get_for_action("run_bash")
    assert resolved is script


def test_get_for_action_raises_if_unsupported():
    registry = PluginRegistry()
    registry.register(DummyPlugin("docker", ["restart"]))

    with pytest.raises(PluginNotFoundError, match="No plugin supports action"):
        registry.get_for_action("run_python")


def test_list_ids_sorted():
    registry = PluginRegistry()
    registry.register_many(
        [
            DummyPlugin("script", ["run_bash"]),
            DummyPlugin("docker", ["restart"]),
        ]
    )

    assert registry.list_ids() == ["docker", "script"]
