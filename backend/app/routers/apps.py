"""Application hosting / lifecycle endpoints."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import (APIRouter, Depends, File, HTTPException, Request,
                     UploadFile, status)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import client_ip, get_current_user
from ..models import Application
from ..schemas import AppCreate, AppOut, AppUpdate, MessageResponse
from ..services import app_manager
from ..services.activity import log_activity
from ..services.notifier import notify_deployment

router = APIRouter(prefix="/api/apps", tags=["apps"], dependencies=[Depends(get_current_user)])

VALID_TYPES = {"python", "flask", "django", "fastapi", "node", "php", "static", "docker"}


@router.get("", response_model=list[AppOut])
async def list_apps(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Application).order_by(Application.name))).scalars().all()
    # Sync running state
    for a in rows:
        a.status = "running" if app_manager.is_running(a) else a.status
    return rows


@router.post("", response_model=AppOut, status_code=201)
async def create_app(payload: AppCreate, request: Request, db: AsyncSession = Depends(get_db)):
    if payload.app_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid app_type. Must be one of {sorted(VALID_TYPES)}")
    existing = await db.execute(select(Application).where(Application.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "App with that name already exists")

    path = app_manager.init_workspace(payload.name)
    app = Application(
        name=payload.name,
        app_type=payload.app_type,
        path=str(path),
        startup_command=payload.startup_command,
        env_vars=payload.env_vars,
        port=payload.port,
        domain=payload.domain,
        auto_restart=payload.auto_restart,
        git_url=payload.git_url,
        git_branch=payload.git_branch,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    await log_activity(db, "app_create", target=app.name, ip=client_ip(request))
    return app


async def _get(db: AsyncSession, app_id: int) -> Application:
    app = await db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "App not found")
    return app


@router.get("/{app_id}", response_model=AppOut)
async def get_app(app_id: int, db: AsyncSession = Depends(get_db)):
    return await _get(db, app_id)


@router.patch("/{app_id}", response_model=AppOut)
async def update_app(
    app_id: int, payload: AppUpdate, request: Request, db: AsyncSession = Depends(get_db)
):
    app = await _get(db, app_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    await db.commit()
    await db.refresh(app)
    await log_activity(db, "app_update", target=app.name, ip=client_ip(request))
    return app


@router.delete("/{app_id}", response_model=MessageResponse)
async def delete_app(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    app_manager.stop_process(app)
    try:
        shutil.rmtree(app.path, ignore_errors=True)
    except OSError:
        pass
    await db.delete(app)
    await db.commit()
    await log_activity(db, "app_delete", target=app.name, ip=client_ip(request))
    return MessageResponse(message=f"Deleted {app.name}")


# ---------- lifecycle ----------
@router.post("/{app_id}/start", response_model=MessageResponse)
async def start_app(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    pid = app_manager.start_process(app)
    app.pid = pid
    app.status = "running"
    await db.commit()
    await log_activity(db, "app_start", target=app.name, ip=client_ip(request))
    return MessageResponse(message=f"Started {app.name} (pid={pid})")


@router.post("/{app_id}/stop", response_model=MessageResponse)
async def stop_app(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    app_manager.stop_process(app)
    app.pid = None
    app.status = "stopped"
    await db.commit()
    await log_activity(db, "app_stop", target=app.name, ip=client_ip(request))
    return MessageResponse(message=f"Stopped {app.name}")


@router.post("/{app_id}/restart", response_model=MessageResponse)
async def restart_app(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    app_manager.stop_process(app)
    pid = app_manager.start_process(app)
    app.pid = pid
    app.status = "running"
    await db.commit()
    await log_activity(db, "app_restart", target=app.name, ip=client_ip(request))
    return MessageResponse(message=f"Restarted {app.name} (pid={pid})")


# ---------- logs ----------
@router.get("/{app_id}/logs")
async def app_logs(app_id: int, lines: int = 200, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    return {"logs": app_manager.read_logs(app, lines=lines)}


# ---------- deployment ----------
@router.post("/{app_id}/deploy/zip", response_model=MessageResponse)
async def deploy_zip(
    app_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    app = await _get(db, app_id)
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Upload must be a .zip file")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        await app_manager.deploy_from_zip(app, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    await log_activity(db, "app_deploy_zip", target=app.name, ip=client_ip(request))
    return MessageResponse(message="Deployed from ZIP")


@router.post("/{app_id}/deploy/git", response_model=MessageResponse)
async def deploy_git(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await _get(db, app_id)
    ok, output = await app_manager.deploy_from_git(app)
    await log_activity(db, "app_deploy_git", target=app.name, ip=client_ip(request),
                       success=ok, detail=output[-500:])
    if not ok:
        raise HTTPException(500, f"Git failed:\n{output}")
    return MessageResponse(message="Git deploy completed")
