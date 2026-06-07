"""
Application configuration.

Loaded from environment variables (and a .env file if present).
Keep secrets OUT of git — the installer generates /etc/pdcloud/pdcloud.env
"""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Core ---
    app_name: str = "PD Cloud Personal"
    app_version: str = "1.0.0"
    env: str = "production"           # production | development
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Security ---
    secret_key: str = secrets.token_urlsafe(64)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12          # 12h sessions
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    csrf_header: str = "X-CSRF-Token"
    bcrypt_rounds: int = 12

    # Login protection
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # --- Paths ---
    data_dir: Path = Path("/var/lib/pdcloud")
    apps_dir: Path = Path("/var/lib/pdcloud/apps")
    backups_dir: Path = Path("/var/lib/pdcloud/backups")
    logs_dir: Path = Path("/var/log/pdcloud")
    db_path: Path = Path("/var/lib/pdcloud/pdcloud.db")

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Resource thresholds for alerts ---
    cpu_alert_pct: float = 90.0
    ram_alert_pct: float = 90.0
    disk_alert_pct: float = 90.0

    # --- Terminal ---
    terminal_shell: str = "/bin/bash"
    terminal_blocked_commands: tuple[str, ...] = (
        "rm -rf /", "mkfs", "shutdown", ":(){:|:&};:", "dd if=", "> /dev/sda",
    )

    # --- CORS ---
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=os.environ.get("PDCLOUD_ENV_FILE", "/etc/pdcloud/pdcloud.env"),
        env_prefix="PDCLOUD_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.apps_dir, self.backups_dir, self.logs_dir):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    try:
        s.ensure_dirs()
    except PermissionError:
        # Fallback for dev — use local ./data
        base = Path(__file__).resolve().parents[2] / "data"
        s.data_dir = base
        s.apps_dir = base / "apps"
        s.backups_dir = base / "backups"
        s.logs_dir = base / "logs"
        s.db_path = base / "pdcloud.db"
        s.ensure_dirs()
    return s


settings = get_settings()
