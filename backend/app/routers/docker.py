"""Docker container & compose endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import client_ip, get_current_user
from ..schemas import DockerComposeRequest, DockerRunRequest, MessageResponse
from ..services import docker_manager
from ..services.activity import log_activity

router = APIRouter(prefix="/api/docker", tags=["docker"],
                   dependencies=[Depends(get_current_user)])


@router.get("/status")
async def status():
    return {"available": docker_manager.DOCKER_AVAILABLE}


@router.get("/containers")
async def containers():
    return docker_manager.list_containers(all_=True)


@router.get("/images")
async def images():
    return docker_manager.list_images()


@router.post("/containers", response_model=MessageResponse)
async def run(payload: DockerRunRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        result = docker_manager.run_container(**payload.model_dump())
    except Exception as e:
        raise HTTPException(500, str(e))
    await log_activity(db, "docker_run", target=result.get("name", ""),
                       ip=client_ip(request))
    return MessageResponse(message=f"Container started: {result['name']} ({result['id']})")


@router.post("/containers/{cid}/start", response_model=MessageResponse)
async def start(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    docker_manager.start(cid)
    await log_activity(db, "docker_start", target=cid, ip=client_ip(request))
    return MessageResponse(message=f"Started {cid}")


@router.post("/containers/{cid}/stop", response_model=MessageResponse)
async def stop(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    docker_manager.stop(cid)
    await log_activity(db, "docker_stop", target=cid, ip=client_ip(request))
    return MessageResponse(message=f"Stopped {cid}")


@router.post("/containers/{cid}/restart", response_model=MessageResponse)
async def restart(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    docker_manager.restart(cid)
    await log_activity(db, "docker_restart", target=cid, ip=client_ip(request))
    return MessageResponse(message=f"Restarted {cid}")


@router.delete("/containers/{cid}", response_model=MessageResponse)
async def remove(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    docker_manager.remove(cid, force=True)
    await log_activity(db, "docker_remove", target=cid, ip=client_ip(request))
    return MessageResponse(message=f"Removed {cid}")


@router.get("/containers/{cid}/logs")
async def logs(cid: str, tail: int = 200):
    return {"logs": docker_manager.logs(cid, tail=tail)}


# ---- Compose ----
@router.post("/compose/up", response_model=MessageResponse)
async def compose_up(
    payload: DockerComposeRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    project_dir = settings.apps_dir / payload.name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "docker-compose.yml").write_text(payload.compose_yaml, encoding="utf-8")
    ok, out = await docker_manager.compose_up(payload.name, str(project_dir))
    await log_activity(db, "docker_compose_up", target=payload.name,
                       ip=client_ip(request), success=ok, detail=out[-500:])
    if not ok:
        raise HTTPException(500, out)
    return MessageResponse(message="Compose up succeeded")


@router.post("/compose/{name}/down", response_model=MessageResponse)
async def compose_down(name: str, request: Request, db: AsyncSession = Depends(get_db)):
    project_dir = settings.apps_dir / name
    ok, out = await docker_manager.compose_down(name, str(project_dir))
    await log_activity(db, "docker_compose_down", target=name,
                       ip=client_ip(request), success=ok)
    if not ok:
        raise HTTPException(500, out)
    return MessageResponse(message="Compose down succeeded")
