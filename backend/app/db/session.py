"""Async SQLAlchemy engine/session."""
from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(_settings.async_database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def create_all() -> None:
    from app.db import models  # noqa: F401 – register models

    async with engine.begin() as conn:
        if _settings.is_postgres:
            try:
                await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            except Exception:
                # Extension may already be enabled or user may not have superuser privileges
                pass
        await conn.run_sync(Base.metadata.create_all)
