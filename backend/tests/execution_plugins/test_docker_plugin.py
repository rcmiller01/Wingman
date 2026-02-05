from __future__ import annotations

import asyncio

from homelab.execution_plugins import DockerPlugin, PluginAction


def test_docker_plugin_restart_success(monkeypatch):
    plugin = DockerPlugin()
    action = PluginAction(action="restart", target="docker://nginx", params={"timeout": 12})

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok, msg

    async def fake_restart(container_id: str, timeout: int = 10):
        assert container_id == "nginx"
        assert timeout == 12
        return True

    monkeypatch.setattr("homelab.execution_plugins.docker_plugin.docker_adapter.restart_container", fake_restart)

    result = asyncio.run(plugin.execute(action))
    assert result["success"] is True
    assert result["plugin_id"] == "docker"
    assert result["action"] == "restart"
    assert result["data"]["container"] == "nginx"

    post_ok, _ = asyncio.run(plugin.validate_post(action, result))
    assert post_ok is True


def test_docker_plugin_validation_rejects_invalid_target():
    plugin = DockerPlugin()
    action = PluginAction(action="restart", target="docker://bad target")

    ok, msg = asyncio.run(plugin.validate_pre(action))

    assert ok is False
    assert "Invalid Docker target format" in msg


def test_docker_plugin_validation_rejects_bad_timeout():
    plugin = DockerPlugin()
    action = PluginAction(action="stop", target="docker://redis", params={"timeout": "abc"})

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok is False
    assert msg == "Timeout must be an integer"


def test_docker_plugin_adapter_failure_surface(monkeypatch):
    plugin = DockerPlugin()
    action = PluginAction(action="start", target="docker://api")

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok, msg

    async def fake_start(container_id: str):
        assert container_id == "api"
        return False

    monkeypatch.setattr("homelab.execution_plugins.docker_plugin.docker_adapter.start_container", fake_start)

    result = asyncio.run(plugin.execute(action))
    assert result["success"] is False
    assert result["error_code"] == "EXECUTION_ERROR"
    assert "Docker action failed" in result["error"]

    post_ok, _ = asyncio.run(plugin.validate_post(action, result))
    assert post_ok is False
