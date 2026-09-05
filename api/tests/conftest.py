import os

# Set env vars before any app module imports so lru_cached get_settings() picks them up
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("USE_DEMO_DATA", "true")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.database import Base, get_db, init_db  # noqa: E402
from app.ingestion.runner import seed_fixture_data  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session", autouse=True)
def configure_db() -> None:
    """Initialise the DB module with the test SQLite database once per session."""
    init_db(TEST_DB_URL)


@pytest.fixture()
async def db():
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        await seed_fixture_data(session)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def client(db):
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()
