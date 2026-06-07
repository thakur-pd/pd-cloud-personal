"""File manager endpoints (browse / upload / download / edit / extract)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import client_ip, get_current_user
from ..schemas import (CreateFolderRequest, FileContent, MessageResponse,
                       RenameRequest)
from ..services import file_manager
from ..services.activity import log_activity

router = APIRouter(prefix="/api/files", tags=["files"], dependencies=[Depends(get_current_user)])


@router.get("/list")
async def list_files(path: str = ""):
    try:
        return file_manager.list_dir(path)
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.get("/read")
async def read_file(path: str):
    try:
        return {"path": path, "content": file_manager.read_text(path)}
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except IsADirectoryError:
        raise HTTPException(400, "Path is a directory")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/write", response_model=MessageResponse)
async def write_file(payload: FileContent, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        file_manager.write_text(payload.path, payload.content)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    await log_activity(db, "file_write", target=payload.path, ip=client_ip(request))
    return MessageResponse(message="Saved")


@router.post("/upload", response_model=MessageResponse)
async def upload(
    path: str = "",
    file: UploadFile = File(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    chunks = []
    while True:
        c = await file.read(1024 * 1024)
        if not c:
            break
        chunks.append(c)
    saved = file_manager.save_upload(path, file.filename or "unnamed", chunks)
    await log_activity(db, "file_upload", target=saved, ip=client_ip(request))
    return MessageResponse(message=f"Uploaded {saved}")


@router.get("/download")
async def download(path: str):
    try:
        full = file_manager.absolute(path)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    if not full.exists() or full.is_dir():
        raise HTTPException(404, "File not found")
    return FileResponse(full, filename=full.name)


@router.delete("/delete", response_model=MessageResponse)
async def delete(path: str, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        file_manager.delete(path)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    await log_activity(db, "file_delete", target=path, ip=client_ip(request))
    return MessageResponse(message=f"Deleted {path}")


@router.post("/rename", response_model=MessageResponse)
async def rename(payload: RenameRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        new = file_manager.rename(payload.path, payload.new_name)
    except (PermissionError, ValueError) as e:
        raise HTTPException(400, str(e))
    await log_activity(db, "file_rename", target=f"{payload.path} -> {new}",
                       ip=client_ip(request))
    return MessageResponse(message=f"Renamed to {new}")


@router.post("/mkdir", response_model=MessageResponse)
async def mkdir(payload: CreateFolderRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        new = file_manager.make_dir(payload.path, payload.name)
    except (PermissionError, ValueError, FileExistsError) as e:
        raise HTTPException(400, str(e))
    await log_activity(db, "file_mkdir", target=new, ip=client_ip(request))
    return MessageResponse(message=f"Created {new}")


@router.post("/extract", response_model=MessageResponse)
async def extract(path: str, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        out = file_manager.extract_zip(path)
    except (PermissionError, ValueError) as e:
        raise HTTPException(400, str(e))
    await log_activity(db, "file_extract", target=out, ip=client_ip(request))
    return MessageResponse(message=f"Extracted to {out}")
