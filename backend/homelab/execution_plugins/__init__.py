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
    "execution_registry",
    "build_default_registry",
]
