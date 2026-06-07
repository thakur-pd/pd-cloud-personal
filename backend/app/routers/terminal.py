"""Browser terminal endpoints (restricted single-command runner + history)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import client_ip, get_current_user
from ..models import TerminalLog
from ..schemas import TerminalCommand, TerminalResult
from ..services.activity import log_activity
from ..services.terminal import TerminalError, run_command

router = APIRouter(prefix="/api/terminal", tags=["terminal"],
                   dependencies=[Depends(get_current_user)])


@router.post("/exec", response_model=TerminalResult)
async def execute(
    payload: TerminalCommand,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        output, code, cwd = await run_command(payload.command, payload.cwd)
    except TerminalError as e:
        raise HTTPException(400, str(e))
    db.add(TerminalLog(command=payload.command, output=output[:5000],
                       exit_code=code, ip=client_ip(request)))
    await db.commit()
    await log_activity(db, "terminal_exec", target=payload.command[:80],
                       ip=client_ip(request), success=(code == 0))
    return TerminalResult(command=payload.command, output=output, exit_code=code, cwd=cwd)


@router.get("/history")
async def history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(TerminalLog).order_by(desc(TerminalLog.created_at)).limit(limit)
    )).scalars().all()
    return [
        {"id": r.id, "command": r.command, "exit_code": r.exit_code,
         "at": r.created_at} for r in rows
    ]
