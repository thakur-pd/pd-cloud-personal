"""Authentication: login, logout, password change."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import client_ip, get_current_user
from ..models import User
from ..schemas import LoginRequest, MessageResponse, PasswordChangeRequest, TokenResponse
from ..security import (
    create_access_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from ..services.activity import log_activity

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = client_ip(request)
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user:
        await log_activity(db, "login", target=payload.username, ip=ip, success=False,
                           detail="unknown user")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Lockout?
    if user.locked_until and user.locked_until > datetime.utcnow():
        await log_activity(db, "login", target=user.username, ip=ip, success=False,
                           detail="account locked")
        raise HTTPException(status.HTTP_423_LOCKED,
                            "Account is locked. Try again later.")

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
        await db.commit()
        await log_activity(db, "login", target=user.username, ip=ip, success=False,
                           detail="bad password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Success
    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    await db.commit()

    token, expires = create_access_token(user.username)
    csrf = generate_csrf_token()

    response.set_cookie(
        "pdcloud_session", token,
        httponly=True, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, max_age=expires, path="/",
    )
    response.set_cookie(
        "csrf_token", csrf,
        httponly=False, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, max_age=expires, path="/",
    )

    await log_activity(db, "login", target=user.username, ip=ip, success=True)
    return TokenResponse(access_token=token, expires_in=expires)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    response.delete_cookie("pdcloud_session", path="/")
    response.delete_cookie("csrf_token", path="/")
    await log_activity(db, "logout", target=user.username, ip=client_ip(request))
    return MessageResponse(message="Logged out")


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "last_login": user.last_login,
        "created_at": user.created_at,
    }


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        await log_activity(db, "password_change", target=user.username,
                           ip=client_ip(request), success=False)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await log_activity(db, "password_change", target=user.username,
                       ip=client_ip(request), success=True)
    return MessageResponse(message="Password updated")
