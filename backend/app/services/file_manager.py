"""
Safe filesystem operations confined to {settings.apps_dir}.

All paths are validated against the apps root to prevent traversal.
"""
from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..config import settings

ROOT: Path = settings.apps_dir


# Disallowed extensions for upload/edit (defensive)
BLOCKED_EXTENSIONS = {".exe", ".dll", ".so.bak"}
MAX_EDIT_BYTES = 2 * 1024 * 1024   # 2 MB cap for in-browser editor


def _resolve(path: str | Path) -> Path:
    """Resolve a user-supplied path against ROOT and ensure containment."""
    p = (ROOT / str(path).lstrip("/")).resolve()
    if not str(p).startswith(str(ROOT.resolve())):
        raise PermissionError(f"Path escapes root: {path}")
    return p


def list_dir(rel: str = "") -> list[dict]:
    target = _resolve(rel)
    if not target.exists():
        return []
    entries = []
    for child in sorted(target.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
        try:
            st = child.stat()
            entries.append({
                "name": child.name,
                "path": str(child.relative_to(ROOT)),
                "is_dir": child.is_dir(),
                "size": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime),
            })
        except OSError:
            continue
    return entries


def read_text(rel: str) -> str:
    target = _resolve(rel)
    if target.is_dir():
        raise IsADirectoryError(rel)
    if target.stat().st_size > MAX_EDIT_BYTES:
        raise ValueError("File too large to edit in-browser")
    return target.read_text(encoding="utf-8", errors="replace")


def write_text(rel: str, content: str) -> None:
    target = _resolve(rel)
    if target.suffix.lower() in BLOCKED_EXTENSIONS:
        raise PermissionError("Blocked file type")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def delete(rel: str) -> None:
    target = _resolve(rel)
    if target == ROOT:
        raise PermissionError("Cannot delete root")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)


def rename(rel: str, new_name: str) -> str:
    target = _resolve(rel)
    if "/" in new_name or "\\" in new_name or new_name in ("", ".", ".."):
        raise ValueError("Invalid name")
    new_path = target.with_name(new_name)
    _resolve(new_path.relative_to(ROOT))  # validate
    target.rename(new_path)
    return str(new_path.relative_to(ROOT))


def make_dir(rel: str, name: str) -> str:
    base = _resolve(rel)
    if "/" in name or "\\" in name:
        raise ValueError("Invalid name")
    new = base / name
    new.mkdir(parents=True, exist_ok=False)
    return str(new.relative_to(ROOT))


def save_upload(rel: str, filename: str, data: Iterable[bytes]) -> str:
    base = _resolve(rel)
    base.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name  # strip any directories
    if Path(safe).suffix.lower() in BLOCKED_EXTENSIONS:
        raise PermissionError("Blocked file type")
    dest = base / safe
    with dest.open("wb") as f:
        for chunk in data:
            f.write(chunk)
    return str(dest.relative_to(ROOT))


def extract_zip(rel: str) -> str:
    target = _resolve(rel)
    if not zipfile.is_zipfile(target):
        raise ValueError("Not a zip file")
    out_dir = target.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target) as zf:
        for member in zf.namelist():
            dest = (out_dir / member).resolve()
            if not str(dest).startswith(str(out_dir.resolve())):
                raise ValueError(f"Unsafe path: {member}")
        zf.extractall(out_dir)
    return str(out_dir.relative_to(ROOT))


def absolute(rel: str) -> Path:
    return _resolve(rel)
