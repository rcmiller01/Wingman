from __future__ import annotations

import asyncio

import importlib

pe_module = importlib.import_module("homelab.control_plane.plan_executor")
from homelab.control_plane.plan_executor import PlanExecutor
from homelab.storage.models import ActionTemplate


class DummyDockerPlugin:
    def __init__(self):
        self.last_action = None

    async def validate_pre(self, action):
        self.last_action = action
        return True, "ok"

    async def execute(self, action):
        return {
            "success": True,
            "plugin_id": "docker",
            "action": action.action,
            "target": action.target,
            "data": {"seen": True},
            "error": None,
            "error_code": None,
        }

    async def validate_post(self, action, result):
        return True, "ok"


def test_extract_effective_params_prefers_nested_params():
    executor = PlanExecutor()

    params = executor._extract_effective_params({"params": {"timeout": 12}, "timeout": 1})

    assert params == {"timeout": 12}


def test_execute_resource_action_routes_docker_through_plugin(monkeypatch):
    executor = PlanExecutor()
    plugin = DummyDockerPlugin()

    monkeypatch.setattr(pe_module.execution_registry, "get", lambda _pid: plugin)

    success, result, error = asyncio.run(
        executor._execute_resource_action(
            action_template=ActionTemplate.restart_resource,
            target="docker://nginx",
            raw_parameters={"params": {"timeout": 15}},
        )
    )

    assert success is True
    assert error is None
    assert result["success"] is True
    assert plugin.last_action.action == "restart"
    assert plugin.last_action.params["timeout"] == 15


def test_execute_resource_action_proxmox_restart_legacy(monkeypatch):
    executor = PlanExecutor()

    async def fake_reboot(node: str, kind: str, vmid: int):
        assert node == "pve"
        assert kind == "qemu"
        assert vmid == 101
        return True

    monkeypatch.setattr(pe_module.proxmox_adapter, "reboot_resource", fake_reboot)

    success, result, error = asyncio.run(
        executor._execute_resource_action(
            action_template=ActionTemplate.restart_resource,
            target="proxmox://pve/qemu/101",
            raw_parameters={},
        )
    )

    assert success is True
    assert error is None
    assert "Reboot sent" in result["message"]
