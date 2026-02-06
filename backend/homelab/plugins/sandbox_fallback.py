"""Fallback sandboxing for Windows/Mac using restricted imports."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# Dangerous modules to block in sandboxed mode
BLOCKED_IMPORTS = {
    "os", "subprocess", "sys", "importlib", "ctypes",
    "multiprocessing", "threading", "socket", "urllib",
    "requests", "httpx", "shutil", "pathlib", "tempfile",
    "pickle", "marshal", "shelve", "dbm", "sqlite3",
    "ftplib", "telnetlib", "smtplib", "poplib", "imaplib",
    "http", "urllib3", "ssl", "email",
}


# Sandbox wrapper script
SANDBOX_WRAPPER = '''
import sys
import builtins

# Block dangerous imports
_original_import = builtins.__import__
_blocked = {blocked_modules}

def _restricted_import(name, *args, **kwargs):
    """Restricted import that blocks dangerous modules."""
    base_module = name.split('.')[0]
    if base_module in _blocked:
        raise ImportError(
            f"Import of '{{name}}' is not allowed in sandboxed mode. "
            f"Sandboxed plugins can only use safe built-in modules."
        )
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _restricted_import

# Restrict built-in functions
_safe_builtins = {{
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod',
    'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr',
    'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'object',
    'oct', 'ord', 'pow', 'print', 'property', 'range', 'repr',
    'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
    'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip',
    '__import__', '__name__', '__doc__', '__package__',
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'AttributeError', 'RuntimeError', 'NotImplementedError',
}}

# Remove dangerous builtins
for name in list(dir(builtins)):
    if name not in _safe_builtins and not name.startswith('_'):
        try:
            delattr(builtins, name)
        except AttributeError:
            pass

# Run plugin script
try:
    with open(r"{script_path}", "r") as f:
        code = f.read()
    exec(code, {{'__name__': '__main__', '__file__': r"{script_path}"}})
except Exception as e:
    print(f"Plugin execution failed: {{e}}", file=sys.stderr)
    sys.exit(1)
'''


async def run_sandboxed_fallback(
    script_path: Path,
    args: list[str] | None = None,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run script in subprocess with restricted imports (fallback for Windows/Mac).
    
    Args:
        script_path: Path to Python script to execute
        args: Command-line arguments (limited support)
        timeout: Execution timeout in seconds
        env: Environment variables (restricted)
    
    Returns:
        Execution result with stdout, stderr, returncode
    
    Raises:
        TimeoutError: If execution exceeds timeout
    """
    args = args or []
    
    # Create wrapper script
    wrapper_code = SANDBOX_WRAPPER.format(
        blocked_modules=repr(BLOCKED_IMPORTS),
        script_path=str(script_path).replace("\\", "\\\\"),
    )
    
    # Prepare environment (minimal, isolated)
    sandbox_env = {
        "PYTHONPATH": "",  # Isolate from system packages
        "PYTHONDONTWRITEBYTECODE": "1",  # Don't create .pyc files
    }
    
    if env:
        # Only allow safe environment variables
        safe_keys = {"PLUGIN_DATA", "PLUGIN_CONFIG"}
        for key, value in env.items():
            if key in safe_keys:
                sandbox_env[key] = value
    
    logger.info(f"Running sandboxed (fallback): {script_path}")
    
    # Run wrapper
    result = await asyncio.create_subprocess_exec(
        "python", "-c", wrapper_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=sandbox_env,
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            result.communicate(),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        result.kill()
        await result.wait()
        raise TimeoutError(f"Script execution exceeded {timeout}s timeout")
    
    return {
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "returncode": result.returncode,
    }
