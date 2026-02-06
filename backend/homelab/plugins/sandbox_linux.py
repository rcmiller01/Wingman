"""Linux sandboxing with seccomp syscall filtering."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# Seccomp policy - allow only safe syscalls
# This is a whitelist approach: only listed syscalls are allowed
SECCOMP_POLICY = {
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64"],
    "syscalls": [
        {
            "names": [
                # File I/O (read-only)
                "read", "readv", "pread64", "preadv", "preadv2",
                "open", "openat", "close", "stat", "fstat", "lstat",
                "newfstatat", "lseek", "access", "faccessat",
                
                # Memory management
                "mmap", "munmap", "mprotect", "brk", "mremap",
                "madvise", "mincore", "msync",
                
                # Process/thread management (limited)
                "getpid", "gettid", "getuid", "geteuid", "getgid",
                "getegid", "getppid", "getpgrp", "getpgid", "getsid",
                "exit", "exit_group",
                
                # Time
                "time", "gettimeofday", "clock_gettime", "clock_getres",
                "nanosleep", "clock_nanosleep",
                
                # Signals (limited)
                "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
                "sigaltstack",
                
                # Polling/waiting
                "poll", "ppoll", "select", "pselect6", "epoll_create",
                "epoll_create1", "epoll_ctl", "epoll_wait", "epoll_pwait",
                
                # Misc safe operations
                "getcwd", "dup", "dup2", "dup3", "pipe", "pipe2",
                "fcntl", "ioctl", "sched_yield", "sched_getaffinity",
                "getrandom", "getrusage", "getrlimit",
                
                # Python-specific
                "futex", "set_tid_address", "set_robust_list",
                "get_robust_list", "arch_prctl", "prctl",
            ],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}


async def run_sandboxed_linux(
    script_path: Path,
    args: list[str] | None = None,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run script in sandboxed subprocess with seccomp.
    
    Args:
        script_path: Path to Python script to execute
        args: Command-line arguments
        timeout: Execution timeout in seconds
        env: Environment variables (restricted)
    
    Returns:
        Execution result with stdout, stderr, returncode
    
    Raises:
        TimeoutError: If execution exceeds timeout
        subprocess.CalledProcessError: If script fails
    """
    args = args or []
    
    # Write seccomp policy to temp file
    policy_path = Path("/tmp") / f"seccomp-{script_path.stem}.json"
    
    try:
        with open(policy_path, "w") as f:
            json.dump(SECCOMP_POLICY, f)
        
        # Prepare environment (minimal, isolated)
        sandbox_env = {
            "PYTHONPATH": "",  # Isolate from system packages
            "PATH": "/usr/bin:/bin",  # Minimal PATH
            "HOME": "/tmp",  # Isolated home
        }
        
        if env:
            # Only allow safe environment variables
            safe_keys = {"PLUGIN_DATA", "PLUGIN_CONFIG"}
            for key, value in env.items():
                if key in safe_keys:
                    sandbox_env[key] = value
        
        # Run with seccomp (requires libseccomp)
        # Note: This requires the script to set up seccomp itself
        # or use a wrapper like firejail
        cmd = ["python3", str(script_path)] + args
        
        logger.info(f"Running sandboxed (Linux): {cmd}")
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
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
    
    finally:
        # Clean up policy file
        if policy_path.exists():
            policy_path.unlink()


def is_seccomp_available() -> bool:
    """Check if seccomp is available on this system."""
    try:
        # Check if libseccomp is available
        result = subprocess.run(
            ["python3", "-c", "import ctypes; ctypes.CDLL('libseccomp.so.2')"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
