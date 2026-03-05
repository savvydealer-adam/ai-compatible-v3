"""asyncpg connection pool with helper functions."""

import logging
from typing import Any

import asyncpg

from server.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    """Return the connection pool, or None if DB is not configured."""
    return _pool


async def init_pool() -> asyncpg.Pool | None:
    """Create the connection pool. Returns None if no database is configured."""
    global _pool  # noqa: PLW0603

    if not settings.database_name:
        logger.info("No database configured — running without persistence")
        return None

    try:
        if settings.database_unix_socket:
            # Cloud SQL Unix socket connection
            dsn = (
                f"postgresql://{settings.database_user}:{settings.database_password}"
                f"@/{settings.database_name}?host={settings.database_unix_socket}"
            )
        else:
            # Standard TCP connection (local dev)
            dsn = (
                f"postgresql://{settings.database_user}:{settings.database_password}"
                f"@{settings.database_host}:{settings.database_port}/{settings.database_name}"
            )

        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        logger.info("Database pool created")
        return _pool
    except Exception:
        logger.exception("Failed to create database pool — running without persistence")
        return None


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool  # noqa: PLW0603
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def execute(query: str, *args: Any) -> str:
    """Execute a query (INSERT/UPDATE/DELETE). Returns status string."""
    if not _pool:
        return ""
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    """Fetch multiple rows."""
    if not _pool:
        return []
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    """Fetch a single row."""
    if not _pool:
        return None
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args: Any) -> Any:
    """Fetch a single value."""
    if not _pool:
        return None
    async with _pool.acquire() as conn:
        return await conn.fetchval(query, *args)
