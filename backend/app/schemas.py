"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


# ---------- Applications ----------
class AppCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    app_type: str
    startup_command: str = ""
    env_vars: dict[str, str] = {}
    port: Optional[int] = None
    domain: Optional[str] = None
    auto_restart: bool = True
    git_url: Optional[str] = None
    git_branch: str = "main"


class AppUpdate(BaseModel):
    startup_command: Optional[str] = None
    env_vars: Optional[dict[str, str]] = None
    port: Optional[int] = None
    domain: Optional[str] = None
    auto_restart: Optional[bool] = None
    git_branch: Optional[str] = None


class AppOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    app_type: str
    path: str
    startup_command: str
    env_vars: dict[str, Any]
    port: Optional[int]
    domain: Optional[str]
    auto_restart: bool
    status: str
    pid: Optional[int]
    git_url: Optional[str]
    git_branch: str
    created_at: datetime
    updated_at: datetime


# ---------- Files ----------
class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime


class FileContent(BaseModel):
    path: str
    content: str


class RenameRequest(BaseModel):
    path: str
    new_name: str


class CreateFolderRequest(BaseModel):
    path: str
    name: str


# ---------- Terminal ----------
class TerminalCommand(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    cwd: Optional[str] = None


class TerminalResult(BaseModel):
    command: str
    output: str
    exit_code: int
    cwd: str


# ---------- Docker ----------
class DockerRunRequest(BaseModel):
    image: str
    name: Optional[str] = None
    ports: dict[str, str] = {}        # "80/tcp": "8080"
    env: dict[str, str] = {}
    volumes: dict[str, str] = {}      # "/host": "/container"
    command: Optional[str] = None
    restart: str = "unless-stopped"


class DockerComposeRequest(BaseModel):
    name: str
    compose_yaml: str


# ---------- DB Manager ----------
class QueryRequest(BaseModel):
    database: str          # "sqlite:/path" or "postgres://..."
    sql: str


# ---------- Settings ----------
class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str


# ---------- Generic ----------
class MessageResponse(BaseModel):
    message: str
    ok: bool = True
