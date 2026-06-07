"""Activity / audit logging service."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ActivityLog


async def log_activity(
    db: AsyncSession,
    action: str,
    *,
    target: str = "",
    detail: str = "",
    ip: str = "",
    success: bool = True,
) -> None:
    entry = ActivityLog(
        action=action, target=target, detail=detail, ip=ip, success=success
    )
    db.add(entry)
    await db.commit()
