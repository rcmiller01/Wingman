"""Execution plugin interfaces, models, errors, and registry."""

from .base import ExecutionPlugin
from .errors import (
    DuplicatePluginError,
    ExecutionPluginError,
    PluginNotFoundError,
    PluginRegistrationError,
    PluginValidationError,
)
from .models import PluginAction, PluginExecutionResult
from .registry import PluginRegistry
from .docker_plugin import DockerPlugin
from .script_plugin import ScriptPlugin
from .bootstrap import execution_registry, build_default_registry

__all__ = [
    "ExecutionPlugin",
    "PluginAction",
    "PluginExecutionResult",
    "PluginRegistry",
    "ExecutionPluginError",
    "PluginRegistrationError",
    "DuplicatePluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "DockerPlugin",
    "ScriptPlugin",
    "execution_registry",
    "build_default_registry",
]
