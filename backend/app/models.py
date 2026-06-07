"""SQLAlchemy ORM models for PD Cloud Personal."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    """The single admin user. Only one row is allowed."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Application(Base):
    """A deployed application managed by the panel."""
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    app_type: Mapped[str] = mapped_column(String(20))   # python|flask|django|fastapi|node|php|static|docker
    path: Mapped[str] = mapped_column(String(500))
    startup_command: Mapped[str] = mapped_column(Text, default="")
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auto_restart: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="stopped")  # running|stopped|crashed
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    git_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    git_branch: Mapped[str] = mapped_column(String(100), default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    logs: Mapped[list["AppLog"]] = relationship(back_populates="app", cascade="all, delete-orphan")


class AppLog(Base):
    """Per-application log line (recent only — stdout/stderr is also on disk)."""
    __tablename__ = "app_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(10), default="info")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    app: Mapped[Application] = relationship(back_populates="logs")


class ActivityLog(Base):
    """Admin activity / audit trail."""
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class TerminalLog(Base):
    """Every command executed via the browser terminal."""
    __tablename__ = "terminal_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    command: Mapped[str] = mapped_column(Text)
    output: Mapped[str] = mapped_column(Text, default="")
    exit_code: Mapped[int] = mapped_column(Integer, default=0)
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class Backup(Base):
    """A backup snapshot record."""
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(20), default="manual")  # manual|scheduled|app
    path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    app_id: Mapped[Optional[int]] = mapped_column(ForeignKey("applications.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class Setting(Base):
    """Simple key/value settings store."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
