"""Backup endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import client_ip, get_current_user
from ..models import Application, Backup
from ..schemas import MessageResponse
from ..services import backup_manager
from ..services.activity import log_activity

router = APIRouter(prefix="/api/backups", tags=["backups"],
                   dependencies=[Depends(get_current_user)])


@router.get("")
async def list_backups(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Backup).order_by(desc(Backup.created_at)))).scalars().all()
    return [
        {"id": b.id, "name": b.name, "kind": b.kind, "size": b.size_bytes,
         "created_at": b.created_at, "app_id": b.app_id}
        for b in rows
    ]


@router.post("/panel", response_model=MessageResponse)
async def backup_panel(request: Request, db: AsyncSession = Depends(get_db)):
    record = await backup_manager.create_backup(db, kind="manual")
    await log_activity(db, "backup_create", target=record.name, ip=client_ip(request))
    return MessageResponse(message=f"Created backup {record.name}")


@router.post("/apps/{app_id}", response_model=MessageResponse)
async def backup_app(app_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    app = await db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "App not found")
    record = await backup_manager.create_backup(db, kind="app", app=app)
    await log_activity(db, "backup_create_app", target=record.name, ip=client_ip(request))
    return MessageResponse(message=f"Created app backup {record.name}")


@router.get("/{backup_id}/download")
async def download(backup_id: int, db: AsyncSession = Depends(get_db)):
    b = await db.get(Backup, backup_id)
    if not b or not Path(b.path).exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(b.path, filename=b.name, media_type="application/gzip")


@router.delete("/{backup_id}", response_model=MessageResponse)
async def delete(backup_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    b = await db.get(Backup, backup_id)
    if not b:
        raise HTTPException(404, "Backup not found")
    backup_manager.delete_backup(b)
    await db.delete(b)
    await db.commit()
    await log_activity(db, "backup_delete", target=b.name, ip=client_ip(request))
    return MessageResponse(message="Deleted")
