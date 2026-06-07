"""
Application lifecycle manager.

Owns the on-disk app workspace, process supervision (subprocess based),
git clone/pull, zip extraction and stdout/stderr capture to per-app logs.

Each managed app lives at:   {settings.apps_dir}/{app.name}/
With logs at:                 {settings.logs_dir}/{app.name}.log

For production it is recommended to also generate a per-app systemd unit
(see deploy/templates/app-systemd.service.j2). The supervisor below is the
in-panel fallback / dev runner.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

import psutil
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Application
from .notifier import notify_crash, notify_deployment

log = logging.getLogger("pdcloud.apps")

# In-memory process table {app_id: Popen}
_PROCESSES: dict[int, subprocess.Popen] = {}


# ---------- workspace ----------
def app_dir(app: Application) -> Path:
    return Path(app.path)


def app_log_file(app: Application) -> Path:
    return settings.logs_dir / f"{app.name}.log"


def init_workspace(name: str) -> Path:
    p = settings.apps_dir / name
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------- deployment ----------
async def deploy_from_zip(app: Application, zip_path: Path) -> None:
    target = Path(app.path)
    target.mkdir(parents=True, exist_ok=True)
    # Clear existing contents
    for child in target.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        # Safe extract — block path traversal
        for member in zf.namelist():
            dest = (target / member).resolve()
            if not str(dest).startswith(str(target.resolve())):
                raise ValueError(f"Unsafe zip member: {member}")
        zf.extractall(target)
    await notify_deployment(app.name, ok=True)


async def deploy_from_git(app: Application) -> tuple[bool, str]:
    if not app.git_url:
        return False, "No git URL configured"
    target = Path(app.path)
    if (target / ".git").exists():
        cmd = ["git", "-C", str(target), "pull", "origin", app.git_branch]
    else:
        target.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "-b", app.git_branch, app.git_url, str(target)]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out, _ = await proc.communicate()
    ok = proc.returncode == 0
    await notify_deployment(app.name, ok=ok)
    return ok, out.decode("utf-8", errors="replace")


# ---------- process supervision ----------
def _build_command(app: Application) -> list[str]:
    if app.startup_command:
        return ["/bin/bash", "-lc", app.startup_command]

    # Sensible defaults per app type
    defaults = {
        "python": ["python3", "main.py"],
        "flask": ["python3", "-m", "flask", "run", "--host=0.0.0.0", f"--port={app.port or 5000}"],
        "django": ["python3", "manage.py", "runserver", f"0.0.0.0:{app.port or 8000}"],
        "fastapi": ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0",
                    "--port", str(app.port or 8000)],
        "node": ["node", "index.js"],
        "php": ["php", "-S", f"0.0.0.0:{app.port or 8080}"],
        "static": ["python3", "-m", "http.server", str(app.port or 8080)],
    }
    return defaults.get(app.app_type, ["echo", "no startup command"])


def start_process(app: Application) -> Optional[int]:
    if app.id in _PROCESSES and _PROCESSES[app.id].poll() is None:
        return _PROCESSES[app.id].pid
    env = os.environ.copy()
    env.update({k: str(v) for k, v in (app.env_vars or {}).items()})
    if app.port:
        env.setdefault("PORT", str(app.port))
    log_path = app_log_file(app)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_path, "ab", buffering=0)
    cmd = _build_command(app)
    proc = subprocess.Popen(
        cmd,
        cwd=app.path,
        env=env,
        stdout=fh,
        stderr=fh,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    _PROCESSES[app.id] = proc
    return proc.pid


def stop_process(app: Application) -> bool:
    proc = _PROCESSES.get(app.id)
    if proc and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    _PROCESSES.pop(app.id, None)
    # Also kill by stored pid (recovery after panel restart)
    if app.pid:
        try:
            p = psutil.Process(app.pid)
            for child in p.children(recursive=True):
                child.terminate()
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    return True


def is_running(app: Application) -> bool:
    proc = _PROCESSES.get(app.id)
    if proc and proc.poll() is None:
        return True
    if app.pid:
        try:
            return psutil.Process(app.pid).is_running()
        except psutil.NoSuchProcess:
            return False
    return False


def read_logs(app: Application, lines: int = 200) -> str:
    log_path = app_log_file(app)
    if not log_path.exists():
        return ""
    try:
        with log_path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = min(size, lines * 200)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
            return "\n".join(data.splitlines()[-lines:])
    except OSError:
        return ""


# ---------- supervisor loop ----------
async def supervise_loop(get_session) -> None:
    """Background task: auto-restart crashed apps and update statuses."""
    from sqlalchemy import select  # local import
    while True:
        await asyncio.sleep(15)
        try:
            async with get_session() as db:  # type: AsyncSession
                rows = (await db.execute(select(Application))).scalars().all()
                for app in rows:
                    running = is_running(app)
                    if app.status == "running" and not running:
                        app.status = "crashed"
                        if app.auto_restart:
                            pid = start_process(app)
                            if pid:
                                app.pid = pid
                                app.status = "running"
                                await notify_crash(app.name, "auto-restarted")
                            else:
                                await notify_crash(app.name, "failed to restart")
                await db.commit()
        except Exception as exc:  # pragma: no cover
            log.warning("supervisor: %s", exc)
