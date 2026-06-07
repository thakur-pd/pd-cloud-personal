"""
Database manager: run queries against the panel's SQLite,
an arbitrary user SQLite file, or a configured PostgreSQL DSN.
"""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

from ..config import settings

try:
    import psycopg  # type: ignore
    PSQL = True
except Exception:
    PSQL = False


def _is_sqlite(dsn: str) -> bool:
    return dsn.startswith("sqlite:") or dsn.endswith(".db") or dsn.endswith(".sqlite")


def list_sqlite_tables(path: str) -> list[str]:
    with sqlite3.connect(path) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in cur.fetchall()]


def run_query(dsn: str, sql: str, limit: int = 500) -> dict[str, Any]:
    if _is_sqlite(dsn):
        path = dsn.replace("sqlite:", "").lstrip("/") if dsn.startswith("sqlite:") else dsn
        if not path.startswith("/"):
            path = "/" + path
        # Restrict SQLite access to the data dir for safety unless an absolute managed path
        if not Path(path).resolve().is_relative_to(settings.data_dir.resolve()) and \
           not Path(path).resolve().is_relative_to(settings.apps_dir.resolve()):
            raise PermissionError("SQLite path outside managed directories")
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql)
            if cur.description is None:
                conn.commit()
                return {"columns": [], "rows": [], "rowcount": cur.rowcount}
            cols = [d[0] for d in cur.description]
            rows = [list(r) for r in cur.fetchmany(limit)]
            return {"columns": cols, "rows": rows, "rowcount": len(rows)}
    elif dsn.startswith(("postgres://", "postgresql://")) and PSQL:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description is None:
                    return {"columns": [], "rows": [], "rowcount": cur.rowcount}
                cols = [c.name for c in cur.description]
                rows = [list(r) for r in cur.fetchmany(limit)]
                return {"columns": cols, "rows": rows, "rowcount": len(rows)}
    else:
        raise ValueError("Unsupported DSN or missing driver")


async def backup_sqlite(src: Path, dest: Path) -> bool:
    def _do():
        with sqlite3.connect(src) as s, sqlite3.connect(dest) as d:
            s.backup(d)
        return True
    return await asyncio.get_event_loop().run_in_executor(None, _do)
