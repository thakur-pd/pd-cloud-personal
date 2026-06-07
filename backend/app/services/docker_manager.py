"""Docker container & compose management (thin wrapper over docker SDK + CLI)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger("pdcloud.docker")

try:
    import docker  # type: ignore
    from docker.errors import DockerException, NotFound  # type: ignore
    _client = None

    def client():
        global _client
        if _client is None:
            _client = docker.from_env()
        return _client
    DOCKER_AVAILABLE = True
except Exception:  # pragma: no cover
    DOCKER_AVAILABLE = False
    DockerException = Exception
    NotFound = Exception
    def client():
        raise RuntimeError("Docker SDK not installed")


def list_containers(all_: bool = True) -> list[dict[str, Any]]:
    if not DOCKER_AVAILABLE:
        return []
    try:
        out = []
        for c in client().containers.list(all=all_):
            out.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "ports": c.ports,
                "created": c.attrs.get("Created", ""),
            })
        return out
    except DockerException as exc:
        log.warning("docker list: %s", exc)
        return []


def list_images() -> list[dict[str, Any]]:
    if not DOCKER_AVAILABLE:
        return []
    try:
        return [
            {"id": i.short_id, "tags": i.tags, "size": i.attrs.get("Size", 0)}
            for i in client().images.list()
        ]
    except DockerException:
        return []


def run_container(
    *,
    image: str,
    name: str | None = None,
    ports: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    volumes: dict[str, str] | None = None,
    command: str | None = None,
    restart: str = "unless-stopped",
) -> dict[str, Any]:
    vols = {h: {"bind": c, "mode": "rw"} for h, c in (volumes or {}).items()}
    container = client().containers.run(
        image,
        name=name,
        detach=True,
        ports={k: int(v) for k, v in (ports or {}).items()},
        environment=env or {},
        volumes=vols,
        command=command,
        restart_policy={"Name": restart},
    )
    return {"id": container.short_id, "name": container.name}


def _get(container_id: str):
    return client().containers.get(container_id)


def start(container_id: str) -> None: _get(container_id).start()
def stop(container_id: str) -> None: _get(container_id).stop(timeout=10)
def restart(container_id: str) -> None: _get(container_id).restart(timeout=10)
def remove(container_id: str, force: bool = True) -> None: _get(container_id).remove(force=force)


def logs(container_id: str, tail: int = 200) -> str:
    try:
        return _get(container_id).logs(tail=tail).decode("utf-8", errors="replace")
    except DockerException as exc:
        return f"error: {exc}"


async def compose_up(project_name: str, working_dir: str) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        "docker", "compose", "-p", project_name, "up", "-d",
        cwd=working_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode == 0, out.decode("utf-8", errors="replace")


async def compose_down(project_name: str, working_dir: str) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        "docker", "compose", "-p", project_name, "down",
        cwd=working_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode == 0, out.decode("utf-8", errors="replace")
