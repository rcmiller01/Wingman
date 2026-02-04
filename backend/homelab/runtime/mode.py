"""Execution mode management.

Single switch: EXECUTION_MODE with values: mock | integration | lab

- MOCK: fast, deterministic, CI-safe
- INTEGRATION: real Docker (local engine), real DB/Qdrant, mocked Proxmox
- LAB: real Proxmox (safe target), real Docker, real DB/Qdrant
"""

import logging
import os
from enum import Enum
from contextvars import ContextVar
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution mode determines which adapters and safety policies are used."""
    
    mock = "mock"
    """Fast, deterministic, CI-safe. All adapters return canned responses."""
    
    integration = "integration"
    """Real Docker (local engine), real DB/Qdrant, mocked Proxmox.
    Docker operations restricted to containers labeled wingman.test=true."""
    
    lab = "lab"
    """Real Proxmox (safe target), real Docker, real DB/Qdrant.
    Requires explicit allowlists and dangerous ops are blocked by default."""


# Context variable for per-request/per-test mode override
_mode_context: ContextVar[Optional[ExecutionMode]] = ContextVar("execution_mode", default=None)

# Module-level default (can be set once at startup)
_default_mode: ExecutionMode = ExecutionMode.mock


def _detect_mode_from_env() -> ExecutionMode:
    """Detect execution mode from environment variables."""
    env_mode = os.environ.get("EXECUTION_MODE", "").lower().strip()
    
    if env_mode == "lab":
        return ExecutionMode.lab
    elif env_mode == "integration":
        return ExecutionMode.integration
    elif env_mode == "mock":
        return ExecutionMode.mock
    
    # Auto-detect based on environment
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return ExecutionMode.mock
    
    if os.environ.get("CI", "").lower() in ("true", "1"):
        return ExecutionMode.mock
    
    # Default to mock for safety
    return ExecutionMode.mock


def get_execution_mode() -> ExecutionMode:
    """Get the current execution mode.
    
    Priority:
    1. Context variable (per-request/per-test override)
    2. Module-level default
    3. Environment variable detection
    """
    # Check context variable first (allows per-test overrides)
    ctx_mode = _mode_context.get()
    if ctx_mode is not None:
        return ctx_mode
    
    return _default_mode


def set_execution_mode(mode: ExecutionMode) -> None:
    """Set the default execution mode.
    
    This should be called once at startup. For per-test overrides,
    use execution_mode_context() instead.
    """
    global _default_mode
    _default_mode = mode
    logger.info(f"[Runtime] Execution mode set to: {mode.value}")


def reset_execution_mode() -> None:
    """Reset to auto-detected mode. Useful for tests."""
    global _default_mode
    _default_mode = _detect_mode_from_env()
    _mode_context.set(None)


class execution_mode_context:
    """Context manager for temporarily changing execution mode.
    
    Usage:
        with execution_mode_context(ExecutionMode.integration):
            # code runs in integration mode
        # back to previous mode
    """
    
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.token = None
    
    def __enter__(self) -> "execution_mode_context":
        self.token = _mode_context.set(self.mode)
        logger.debug(f"[Runtime] Entered execution mode context: {self.mode.value}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _mode_context.reset(self.token)
        logger.debug("[Runtime] Exited execution mode context")
        return None


class async_execution_mode_context:
    """Async context manager for temporarily changing execution mode."""
    
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.token = None
    
    async def __aenter__(self) -> "async_execution_mode_context":
        self.token = _mode_context.set(self.mode)
        logger.debug(f"[Runtime] Entered async execution mode context: {self.mode.value}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        _mode_context.reset(self.token)
        logger.debug("[Runtime] Exited async execution mode context")
        return None


# Convenience functions
def is_mock_mode() -> bool:
    """Check if currently in mock mode."""
    return get_execution_mode() == ExecutionMode.mock


def is_integration_mode() -> bool:
    """Check if currently in integration mode."""
    return get_execution_mode() == ExecutionMode.integration


def is_lab_mode() -> bool:
    """Check if currently in lab mode."""
    return get_execution_mode() == ExecutionMode.lab


def should_execute_real() -> bool:
    """Check if real execution should occur (not mock)."""
    return get_execution_mode() in (ExecutionMode.integration, ExecutionMode.lab)


def get_mode_description() -> str:
    """Get human-readable description of current mode."""
    mode = get_execution_mode()
    descriptions = {
        ExecutionMode.mock: "Mock mode - all operations return canned responses",
        ExecutionMode.integration: "Integration mode - real Docker, mocked Proxmox",
        ExecutionMode.lab: "Lab mode - real infrastructure with safety constraints",
    }
    return descriptions.get(mode, f"Unknown mode: {mode}")


# Initialize default mode from environment
_default_mode = _detect_mode_from_env()
logger.info(f"[Runtime] Initial execution mode: {_default_mode.value}")
