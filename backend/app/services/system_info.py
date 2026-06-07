"""System resource collection (CPU / RAM / disk / network / load / uptime)."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import psutil

_BOOT_TIME = psutil.boot_time()


def cpu_snapshot() -> dict[str, Any]:
    return {
        "percent": psutil.cpu_percent(interval=None),
        "count": psutil.cpu_count(logical=True),
        "physical": psutil.cpu_count(logical=False),
        "per_core": psutil.cpu_percent(interval=None, percpu=True),
        "freq": getattr(psutil.cpu_freq(), "current", 0) or 0,
    }


def ram_snapshot() -> dict[str, Any]:
    v = psutil.virtual_memory()
    s = psutil.swap_memory()
    return {
        "total": v.total,
        "used": v.used,
        "available": v.available,
        "percent": v.percent,
        "swap_total": s.total,
        "swap_used": s.used,
        "swap_percent": s.percent,
    }


def disk_snapshot(path: str = "/") -> dict[str, Any]:
    try:
        d = psutil.disk_usage(path)
        return {"total": d.total, "used": d.used, "free": d.free, "percent": d.percent}
    except OSError:
        return {"total": 0, "used": 0, "free": 0, "percent": 0}


_LAST_NET = {"t": time.time(), "io": psutil.net_io_counters()}


def network_snapshot() -> dict[str, Any]:
    global _LAST_NET
    now = time.time()
    cur = psutil.net_io_counters()
    dt = max(now - _LAST_NET["t"], 1e-3)
    rx_rate = (cur.bytes_recv - _LAST_NET["io"].bytes_recv) / dt
    tx_rate = (cur.bytes_sent - _LAST_NET["io"].bytes_sent) / dt
    _LAST_NET = {"t": now, "io": cur}
    return {
        "bytes_recv": cur.bytes_recv,
        "bytes_sent": cur.bytes_sent,
        "rx_rate": rx_rate,
        "tx_rate": tx_rate,
    }


def load_snapshot() -> dict[str, Any]:
    try:
        l1, l5, l15 = psutil.getloadavg()
    except (AttributeError, OSError):
        l1 = l5 = l15 = 0.0
    return {"1m": l1, "5m": l5, "15m": l15}


def uptime_snapshot() -> dict[str, Any]:
    secs = int(time.time() - _BOOT_TIME)
    return {
        "seconds": secs,
        "boot_time": datetime.fromtimestamp(_BOOT_TIME).isoformat(),
        "pretty": _human_uptime(secs),
    }


def _human_uptime(seconds: int) -> str:
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def running_services() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in psutil.process_iter(["pid", "name", "username", "status", "cpu_percent"]):
        try:
            info = p.info
            if info.get("status") == psutil.STATUS_RUNNING:
                out.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    out.sort(key=lambda x: (x.get("cpu_percent") or 0), reverse=True)
    return out[:20]


def full_snapshot() -> dict[str, Any]:
    return {
        "cpu": cpu_snapshot(),
        "ram": ram_snapshot(),
        "disk": disk_snapshot("/"),
        "network": network_snapshot(),
        "load": load_snapshot(),
        "uptime": uptime_snapshot(),
        "timestamp": datetime.utcnow().isoformat(),
    }
