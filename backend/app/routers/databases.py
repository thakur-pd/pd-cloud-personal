"""Database manager endpoints (SQLite + PostgreSQL)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import client_ip, get_current_user
from ..schemas import MessageResponse, QueryRequest
from ..services import db_manager
from ..services.activity import log_activity

router = APIRouter(prefix="/api/db", tags=["db"], dependencies=[Depends(get_current_user)])


@router.get("/tables")
async def tables(path: str):
    try:
        return {"tables": db_manager.list_sqlite_tables(path)}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/query")
async def query(payload: QueryRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        result = db_manager.run_query(payload.database, payload.sql)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))
    await log_activity(db, "db_query", target=payload.database,
                       ip=client_ip(request), detail=payload.sql[:200])
    return result
