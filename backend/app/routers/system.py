"""System monitoring + dashboard endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import ActivityLog, AppLog, Application
from ..services import system_info

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(get_current_user)])


@router.get("/snapshot")
async def snapshot():
    return system_info.full_snapshot()


@router.get("/services")
async def services():
    return system_info.running_services()


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    snap = system_info.full_snapshot()
    # App counts
    total_apps = (await db.execute(select(func.count()).select_from(Application))).scalar() or 0
    running_apps = (await db.execute(
        select(func.count()).select_from(Application).where(Application.status == "running")
    )).scalar() or 0

    # Recent activity
    activities = (await db.execute(
        select(ActivityLog).order_by(desc(ActivityLog.created_at)).limit(10)
    )).scalars().all()

    # Recent logs across apps
    logs = (await db.execute(
        select(AppLog).order_by(desc(AppLog.created_at)).limit(20)
    )).scalars().all()

    return {
        "system": snap,
        "apps": {"total": total_apps, "running": running_apps},
        "activities": [
            {
                "action": a.action, "target": a.target, "detail": a.detail,
                "success": a.success, "ip": a.ip, "at": a.created_at,
            }
            for a in activities
        ],
        "logs": [
            {"app_id": l.app_id, "level": l.level, "message": l.message, "at": l.created_at}
            for l in logs
        ],
    }
