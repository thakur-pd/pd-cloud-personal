"""
Browser terminal service.

This is a *restricted* command runner (NOT a full PTY). Each request runs
a single shell command via /bin/bash -lc, with output captured and audited.
Destructive commands are blocked. Working directory is constrained to either
the home dir or a managed app directory.

For a richer PTY experience, a future version can integrate xterm.js +
WebSocket + pty.spawn — kept out of scope for the initial single-admin panel.
"""
from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Optional

from ..config import settings


class TerminalError(Exception):
    pass


def _is_blocked(command: str) -> bool:
    low = command.lower()
    return any(b in low for b in settings.terminal_blocked_commands)


async def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 30,
) -> tuple[str, int, str]:
    if not command.strip():
        raise TerminalError("Empty command")
    if _is_blocked(command):
        raise TerminalError("Command blocked by security policy")

    working_dir = Path(cwd) if cwd else settings.apps_dir
    if not working_dir.exists():
        working_dir = settings.apps_dir

    # Always run as login shell so user PATH is correct
    proc = await asyncio.create_subprocess_exec(
        settings.terminal_shell, "-lc", command,
        cwd=str(working_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return ("[command timed out]", 124, str(working_dir))
    return (out.decode("utf-8", errors="replace"), proc.returncode or 0, str(working_dir))


def safe_shlex(command: str) -> list[str]:
    return shlex.split(command)
