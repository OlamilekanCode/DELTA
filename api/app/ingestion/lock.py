"""Database-backed job lock using PostgreSQL advisory locks.

On SQLite (development / tests) no lock is applied — SQLite is single-process
and the PID-file lock in the CLI entry point is sufficient.

Usage (from cron endpoints):
    from app.ingestion.lock import advisory_lock, JobAlreadyRunningErrorError

    try:
        async with advisory_lock("refresh-crypto-quotes"):
            await do_work()
    except JobAlreadyRunningErrorError:
        return {"ok": False, "skipped": True}
"""

import contextlib
from typing import AsyncIterator

from sqlalchemy import text

from app.database import get_engine


class JobAlreadyRunningError(Exception):
    pass


@contextlib.asynccontextmanager
async def advisory_lock(job_name: str) -> AsyncIterator[None]:
    """Acquire a PostgreSQL session-level advisory lock for the duration of the context.

    * Raises JobAlreadyRunningError immediately if another server instance holds the lock.
    * On SQLite the context is entered with no locking (single-process environment).
    * The lock is released when the context exits, regardless of success or failure.
    """
    # Stable 31-bit integer derived from the job name
    lock_id = sum(ord(c) for c in job_name) % (2**31 - 1)
    dialect = get_engine().dialect.name

    if dialect != "postgresql":
        yield
        return

    async with get_engine().connect() as conn:
        result = await conn.execute(text(f"SELECT pg_try_advisory_lock({lock_id})"))
        acquired = result.scalar()
        if not acquired:
            raise JobAlreadyRunningError(
                f"Job '{job_name}' is already running on another instance"
            )
        try:
            yield
        finally:
            await conn.execute(text(f"SELECT pg_advisory_unlock({lock_id})"))
