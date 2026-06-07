"""
PD Cloud Personal — FastAPI application entrypoint.

Mounts:
  /api/...        -> JSON REST endpoints (auth required except /api/auth/login)
  /static/...     -> Frontend assets
  /               -> Frontend SPA shell (index.html); SPA handles client routing
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import SessionLocal, db_session, init_db
from .routers import (apps, auth, backups, databases, docker, files,
                      notifications, system, terminal)
from .security import SecurityHeadersMiddleware, verify_csrf
from .services.app_manager import supervise_loop
from .services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("pdcloud")

# Rate limiter — applied globally; tighter limit on /api/auth/login below
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Load persisted Telegram settings into in-memory settings
    from sqlalchemy import select
    from .models import Setting
    async with db_session() as db:
        token = (await db.execute(select(Setting).where(Setting.key == "telegram_bot_token"))).scalar_one_or_none()
        chat = (await db.execute(select(Setting).where(Setting.key == "telegram_chat_id"))).scalar_one_or_none()
        if token: settings.telegram_bot_token = token.value
        if chat:  settings.telegram_chat_id   = chat.value
    start_scheduler()
    import asyncio
    sup_task = asyncio.create_task(supervise_loop(db_session))
    log.info("PD Cloud Personal %s started", settings.app_version)
    try:
        yield
    finally:
        sup_task.cancel()
        stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

# --- Middlewares ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.cookie_secure,
    same_site=settings.cookie_samesite,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global CSRF gate for state-changing API requests ---
@app.middleware("http")
async def csrf_gate(request: Request, call_next):
    # Allow auth login & test endpoints without CSRF (they set the cookie),
    # require CSRF for all other state-changing /api/* calls.
    path = request.url.path
    if path.startswith("/api/") and path not in ("/api/auth/login",):
        try:
            verify_csrf(request)
        except Exception as exc:
            return JSONResponse({"detail": str(exc.detail) if hasattr(exc, "detail") else str(exc)},
                                status_code=403)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Tighter rate limit on login
limiter.limit("10/minute")(auth.login)

# --- Routers ---
app.include_router(auth.router)
app.include_router(system.router)
app.include_router(apps.router)
app.include_router(files.router)
app.include_router(terminal.router)
app.include_router(docker.router)
app.include_router(databases.router)
app.include_router(backups.router)
app.include_router(notifications.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


# --- Frontend ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str):
    # Serve the SPA shell for any non-/api/ route
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    index = FRONTEND_DIR / "pages" / "index.html"
    return FileResponse(index)
