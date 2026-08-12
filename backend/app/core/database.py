"""
Async SQLAlchemy database engine and session management.
Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from app.core.config import settings

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    metadata = metadata


# Engine kwarg handling for SQLite vs Postgres
engine_kwargs: dict[str, Any] = {
    "echo": settings.DATABASE_ECHO,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables and auto-migrate missing columns for local development."""
    import app.models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # SQLite column sync check
        if "sqlite" in settings.DATABASE_URL:
            def _sync_columns(sync_conn):
                from sqlalchemy import inspect, text
                inspector = inspect(sync_conn)
                for table_name, table in Base.metadata.tables.items():
                    if inspector.has_table(table_name):
                        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
                        for col in table.columns:
                            if col.name not in existing_cols:
                                col_type = col.type.compile(sync_conn.dialect)
                                default_sql = ""
                                default_arg = getattr(col.default, "arg", None) if col.default is not None else None
                                if default_arg is not None:
                                    default_sql = f" DEFAULT {default_arg}"
                                elif not col.nullable:
                                    col_type_upper = col_type.upper()
                                    if "INT" in col_type_upper:
                                        default_sql = " DEFAULT 0"
                                    elif "BOOL" in col_type_upper:
                                        default_sql = " DEFAULT 0"
                                    else:
                                        default_sql = " DEFAULT ''"
                                sync_conn.execute(
                                    text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}{default_sql}')
                                )
            await conn.run_sync(_sync_columns)


async def drop_tables() -> None:
    """Drop all tables (for testing only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
