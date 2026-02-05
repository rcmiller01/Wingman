"""Typed errors for execution plugins and registry operations."""


class ExecutionPluginError(Exception):
    """Base class for execution plugin related errors."""


class PluginRegistrationError(ExecutionPluginError):
    """Raised when plugin registration fails."""


class DuplicatePluginError(PluginRegistrationError):
    """Raised when registering a plugin with an existing plugin_id."""


class PluginNotFoundError(ExecutionPluginError):
    """Raised when a plugin cannot be found by identifier or action."""


class PluginValidationError(ExecutionPluginError):
    """Raised when plugin pre/post validation fails."""
