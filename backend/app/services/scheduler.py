"""Background scheduler for resource alerts and scheduled backups."""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import settings
from . import system_info
from .notifier import notify_resource_alert

log = logging.getLogger("pdcloud.scheduler")

scheduler: AsyncIOScheduler = AsyncIOScheduler()


async def _resource_watch() -> None:
    snap = system_info.full_snapshot()
    cpu = snap["cpu"]["percent"]
    ram = snap["ram"]["percent"]
    disk = snap["disk"]["percent"]
    if cpu >= settings.cpu_alert_pct:
        await notify_resource_alert("cpu", cpu, settings.cpu_alert_pct)
    if ram >= settings.ram_alert_pct:
        await notify_resource_alert("ram", ram, settings.ram_alert_pct)
    if disk >= settings.disk_alert_pct:
        await notify_resource_alert("disk", disk, settings.disk_alert_pct)


async def _scheduled_backup() -> None:
    from ..database import db_session
    from .backup_manager import create_backup
    async with db_session() as db:
        await create_backup(db, kind="scheduled")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(_resource_watch, "interval", minutes=2, id="resource_watch", replace_existing=True)
    scheduler.add_job(_scheduled_backup, "cron", hour=3, minute=0, id="nightly_backup", replace_existing=True)
    scheduler.start()
    log.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
  
