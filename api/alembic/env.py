import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

# Load .env so DATABASE_URL is available when running alembic from the CLI
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object — gives access to values in alembic.ini
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DATABASE_URL from environment; env.py owns this, not alembic.ini
_raw_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
# Normalise plain postgresql:// / postgres:// to use the asyncpg driver
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://"):
    _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = _raw_url
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Import metadata here so Alembic can detect schema changes
import app.models  # noqa: E402, F401 — ensure all models are registered
from app.database import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Required for SQLite ALTER TABLE compatibility
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
