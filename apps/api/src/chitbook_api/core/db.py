"""Database engine, session and declarative base."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from chitbook_api.core.config import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def database_url(db_name: str | None = None) -> URL:
    s = get_settings()
    return URL.create(
        "postgresql+asyncpg",
        username=s.db_user,
        password=s.db_password.get_secret_value(),
        host=s.db_host,
        port=s.db_port,
        database=db_name or s.db_name,
    )


@lru_cache
def get_engine() -> AsyncEngine:
    s = get_settings()
    return create_async_engine(
        database_url(),
        pool_size=s.db_pool_size,
        max_overflow=s.db_pool_max_overflow,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": s.tz, "application_name": "chitbook-api"}},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one transaction per request, committed on success."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
