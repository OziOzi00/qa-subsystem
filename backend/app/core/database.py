"""MySQL connection pool and query utilities.

Infrastructure code that supports the feedback and admin services.
"""

import logging
from urllib.parse import urlparse

from aiomysql import Pool, create_pool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Pool | None = None


async def init_pool() -> None:
    """Create the global connection pool from MYSQL_DSN."""
    global _pool
    if _pool is not None:
        return
    dsn = settings.MYSQL_DSN
    if not dsn:
        logger.warning("MYSQL_DSN is not configured. DB endpoints will be unavailable.")
        return

    # Normalise scheme so urlparse understands it
    raw = dsn.replace("mysql+pymysql://", "mysql://", 1)
    parsed = urlparse(raw)

    try:
        _pool = await create_pool(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=parsed.password or "",
            db=(parsed.path or "/seitem").lstrip("/"),
            minsize=1,
            maxsize=5,
            charset="utf8mb4",
            autocommit=True,
        )
    except Exception:
        logger.exception(
            "Failed to connect to MySQL at %s:%s. "
            "DB-backed endpoints will return errors.",
            parsed.hostname,
            parsed.port,
        )


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        pool = _pool
        _pool = None
        pool.close()
        await pool.wait_closed()


async def execute(sql: str, *args) -> int:
    """Execute a write statement and return the number of affected rows."""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args or None)
            return cur.rowcount


async def fetch_one(sql: str, *args) -> tuple | None:
    """Return the first row of a query, or None."""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args or None)
            return await cur.fetchone()


async def fetch_all(sql: str, *args) -> list[tuple]:
    """Return all rows of a query."""
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args or None)
            return await cur.fetchall()


async def insert_and_get_id(sql: str, *args) -> int:
    """Insert a row and return its auto-increment id.

    Guarantees the id comes from the *same* connection as the insert.
    """
    pool = _require_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args or None)
            await cur.execute("SELECT LAST_INSERT_ID()")
            row = await cur.fetchone()
            return row[0] if row else 0


def _require_pool() -> Pool:
    if _pool is None:
        raise RuntimeError(
            "Database pool is not initialised. "
            "Call init_pool() during app startup."
        )
    return _pool
