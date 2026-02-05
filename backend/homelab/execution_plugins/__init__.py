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
]
