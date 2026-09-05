from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict[str, Any]:
    return {"check_same_thread": False} if "sqlite" in url else {}


class _State:
    engine: AsyncEngine | None = None
    factory: async_sessionmaker[AsyncSession] | None = None


_state = _State()


def init_db(url: str) -> None:
    _state.engine = create_async_engine(url, echo=False, connect_args=_connect_args(url))
    _state.factory = async_sessionmaker(_state.engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    assert _state.engine is not None, "DB not initialised"
    return _state.engine


def get_factory() -> async_sessionmaker[AsyncSession]:
    assert _state.factory is not None, "DB not initialised"
    return _state.factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_factory()
    async with factory() as session:
        yield session
