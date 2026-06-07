"""Async SQLAlchemy engine and session factory for SQLite."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
    connect_args={"check_same_thread": False},
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables (called once on startup)."""
    # Import here to register models with Base.metadata
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    """Context manager for use outside of FastAPI dependencies."""
    async with SessionLocal() as session:
        yield session
