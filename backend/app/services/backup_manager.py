"""Backup creation, listing, restore, and snapshots."""
from __future__ import annotations

import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Application, Backup
from .notifier import notify_backup


def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


async def create_backup(
    db: AsyncSession,
    *,
    kind: str = "manual",
    app: Optional[Application] = None,
) -> Backup:
    """
    Backup either the whole panel data dir (kind=manual|scheduled)
    or a single application directory (kind=app).
    """
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    if app:
        name = f"app-{app.name}-{_ts()}.tar.gz"
        src = Path(app.path)
    else:
        name = f"panel-{kind}-{_ts()}.tar.gz"
        src = settings.data_dir

    out = settings.backups_dir / name
    with tarfile.open(out, "w:gz") as tar:
        tar.add(src, arcname=src.name)

    record = Backup(
        name=name,
        kind=kind if not app else "app",
        path=str(out),
        size_bytes=out.stat().st_size,
        app_id=app.id if app else None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    await notify_backup(name, ok=True)
    return record


def restore_backup(backup: Backup, target: Path) -> bool:
    src = Path(backup.path)
    if not src.exists():
        return False
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src, "r:gz") as tar:
        # Block path traversal
        for m in tar.getmembers():
            if m.name.startswith("/") or ".." in Path(m.name).parts:
                return False
        tar.extractall(target)
    return True


def delete_backup(backup: Backup) -> None:
    try:
        Path(backup.path).unlink(missing_ok=True)
    except OSError:
        pass


def list_files() -> list[dict]:
    if not settings.backups_dir.exists():
        return []
    return [
        {
            "name": p.name,
            "size": p.stat().st_size,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        }
        for p in sorted(settings.backups_dir.iterdir(), reverse=True)
        if p.is_file()
    ]
