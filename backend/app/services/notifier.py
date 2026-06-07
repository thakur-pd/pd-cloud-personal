"""
Telegram notification service.

Configure via the Settings page in the UI or PDCLOUD_TELEGRAM_BOT_TOKEN /
PDCLOUD_TELEGRAM_CHAT_ID env vars.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from ..config import settings

log = logging.getLogger("pdcloud.notifier")

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


async def send_telegram(
    text: str,
    *,
    token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    token = token or settings.telegram_bot_token
    chat_id = chat_id or settings.telegram_chat_id
    if not token or not chat_id:
        return False

    url = _TELEGRAM_URL.format(token=token)
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            return r.status_code == 200
    except Exception as exc:  # pragma: no cover
        log.warning("Telegram notification failed: %s", exc)
        return False


async def notify_deployment(app_name: str, ok: bool = True) -> None:
    icon = "✅" if ok else "❌"
    await send_telegram(f"{icon} *Deployment* `{app_name}` {'succeeded' if ok else 'failed'}")


async def notify_crash(app_name: str, reason: str = "") -> None:
    await send_telegram(f"💥 *App crashed:* `{app_name}`\n{reason}")


async def notify_resource_alert(metric: str, value: float, threshold: float) -> None:
    await send_telegram(
        f"⚠️ *Resource Alert* — {metric.upper()} at *{value:.1f}%* "
        f"(threshold {threshold:.0f}%)"
    )


async def notify_backup(name: str, ok: bool = True) -> None:
    icon = "💾" if ok else "❌"
    await send_telegram(f"{icon} Backup `{name}` {'completed' if ok else 'failed'}")
