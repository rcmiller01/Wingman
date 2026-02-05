from __future__ import annotations

import asyncio

from homelab.execution_plugins import PluginAction, ScriptPlugin


def test_script_plugin_run_bash_success():
    plugin = ScriptPlugin()
    action = PluginAction(
        action="run_bash",
        target="local://worker",
        params={"command": "echo hello", "timeout": 5},
    )

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok, msg

    result = asyncio.run(plugin.execute(action))
    assert result["success"] is True
    assert result["plugin_id"] == "script"
    assert result["data"]["exit_code"] == 0
    assert "hello" in result["data"]["stdout"]


def test_script_plugin_blocks_dangerous_bash_command():
    plugin = ScriptPlugin()
    action = PluginAction(
        action="run_bash",
        target="local://worker",
        params={"command": "rm -rf /tmp/demo"},
    )

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok is False
    assert msg == "Script contains blocked operation"


def test_script_plugin_timeout_failure():
    plugin = ScriptPlugin()
    action = PluginAction(
        action="run_python",
        target="local://worker",
        params={"code": "import time; time.sleep(2)", "timeout": 1},
    )

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok, msg

    result = asyncio.run(plugin.execute(action))
    assert result["success"] is False
    assert result["error_code"] == "EXECUTION_ERROR"
    assert "timed out" in result["error"]


def test_script_plugin_rejects_invalid_timeout_type():
    plugin = ScriptPlugin()
    action = PluginAction(
        action="run_python",
        target="local://worker",
        params={"code": "print('ok')", "timeout": "NaN"},
    )

    ok, msg = asyncio.run(plugin.validate_pre(action))
    assert ok is False
    assert msg == "Timeout must be an integer"
