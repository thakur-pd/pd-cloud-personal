"""Telegram notification config & test endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import client_ip, get_current_user
from ..models import Setting
from ..schemas import MessageResponse, TelegramConfig
from ..services.activity import log_activity
from ..services.notifier import send_telegram

router = APIRouter(prefix="/api/notifications", tags=["notifications"],
                   dependencies=[Depends(get_current_user)])


async def _set(db: AsyncSession, key: str, value: str) -> None:
    s = await db.get(Setting, key)
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))


@router.get("/telegram")
async def get_telegram(db: AsyncSession = Depends(get_db)):
    token = (await db.get(Setting, "telegram_bot_token"))
    chat = (await db.get(Setting, "telegram_chat_id"))
    return {
        "bot_token": (token.value if token else settings.telegram_bot_token)[:6] + "…"
                     if (token or settings.telegram_bot_token) else "",
        "chat_id": chat.value if chat else settings.telegram_chat_id,
        "configured": bool((token and token.value) or settings.telegram_bot_token),
    }


@router.post("/telegram", response_model=MessageResponse)
async def set_telegram(
    payload: TelegramConfig, request: Request, db: AsyncSession = Depends(get_db)
):
    await _set(db, "telegram_bot_token", payload.bot_token)
    await _set(db, "telegram_chat_id", payload.chat_id)
    await db.commit()
    # Refresh in-memory settings
    settings.telegram_bot_token = payload.bot_token
    settings.telegram_chat_id = payload.chat_id
    await log_activity(db, "telegram_config", ip=client_ip(request))
    return MessageResponse(message="Telegram updated")


@router.post("/telegram/test", response_model=MessageResponse)
async def test_telegram():
    ok = await send_telegram("🔔 PD Cloud Personal — test notification")
    return MessageResponse(message="Sent" if ok else "Failed (check config)", ok=ok)
