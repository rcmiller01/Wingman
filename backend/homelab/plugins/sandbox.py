"""Plugin sandboxing - platform-aware execution."""

from __future__ import annotations

import logging
import platform
from pathlib import Path
from typing import Any

from homelab.plugins.manifest_schema import TrustLevel


logger = logging.getLogger(__name__)


# Lazy imports to avoid import-time failures
_sandbox_linux = None
_sandbox_fallback = None


def _get_sandbox_backend():
    """Get appropriate sandbox backend for current platform."""
    global _sandbox_linux, _sandbox_fallback
    
    system = platform.system()
    
    if system == "Linux":
        # Try Linux seccomp first
        if _sandbox_linux is None:
            try:
                from homelab.plugins import sandbox_linux
                _sandbox_linux = sandbox_linux
                
                if sandbox_linux.is_seccomp_available():
                    logger.info("Using Linux seccomp sandboxing")
                    return _sandbox_linux
                else:
                    logger.warning("seccomp not available, falling back to restricted imports")
            except ImportError as e:
                logger.warning(f"Failed to import Linux sandbox: {e}")
    
    # Fallback for Windows/Mac or if Linux seccomp unavailable
    if _sandbox_fallback is None:
        from homelab.plugins import sandbox_fallback
        _sandbox_fallback = sandbox_fallback
        logger.info(f"Using fallback sandboxing for {system}")
    
    return _sandbox_fallback


async def run_sandboxed(
    script_path: Path,
    trust_level: TrustLevel,
    args: list[str] | None = None,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run script with appropriate sandboxing based on trust level.
    
    Args:
        script_path: Path to script to execute
        trust_level: Plugin trust level
        args: Command-line arguments
        timeout: Execution timeout in seconds
        env: Environment variables
    
    Returns:
        Execution result with stdout, stderr, returncode
    
    Raises:
        ValueError: If trust level is invalid
        TimeoutError: If execution exceeds timeout
    """
    if trust_level == TrustLevel.TRUSTED:
        # Trusted plugins run without sandboxing
        logger.info(f"Running trusted plugin: {script_path}")
        # TODO: Implement direct execution for trusted plugins
        raise NotImplementedError("Trusted plugin execution not yet implemented")
    
    elif trust_level in (TrustLevel.VERIFIED, TrustLevel.SANDBOXED):
        # Verified and sandboxed plugins run in sandbox
        backend = _get_sandbox_backend()
        
        if hasattr(backend, "run_sandboxed_linux"):
            return await backend.run_sandboxed_linux(
                script_path, args, timeout, env
            )
        else:
            return await backend.run_sandboxed_fallback(
                script_path, args, timeout, env
            )
    
    else:
        raise ValueError(f"Invalid trust level: {trust_level}")
