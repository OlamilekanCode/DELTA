import os

# Set env vars before any app module imports so lru_cached get_settings() picks them up.
# APP_ENV in particular must never fall through to a developer's local .env
# file here — Settings(**overrides) in individual tests still reads it for
# any field the test doesn't explicitly override, and a stray
# APP_ENV=production in .env must never silently make the suite believe it's
# running in production (e.g. tripping production-only fail-closed checks).
os.environ.setdefault("APP_ENV", "test")
# A plain, unshared placeholder at import time — app.main's `app = create_app()`
# (imported below) calls get_settings() eagerly, so *some* valid value must
# exist before that import. The REAL, worker-aware value tests actually
# connect to is computed by _test_db_url() below and used directly by the
# fixtures — get_settings()'s cached copy of this is never consulted for
# picking the physical SQLite file (init_db() here is always called with
# _test_db_url(), never settings.database_url).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("USE_DEMO_DATA", "true")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-xyz")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.database import Base, get_db, init_db  # noqa: E402
from app.ingestion.runner import seed_fixture_data  # noqa: E402
from app.main import app  # noqa: E402
from app.services.scoring import recompute_all_scores  # noqa: E402


def _test_db_url() -> str:
    """Each pytest-xdist worker gets its own SQLite file — the `db` fixture
    create_all()/drop_all()s a fresh schema per test, and multiple worker
    processes hitting the SAME physical file concurrently corrupts it
    ("no such table" mid-run, races between one worker's DROP and another's
    INSERT). Called from inside fixtures (never at module import time) —
    PYTEST_XDIST_WORKER is only reliably set by the time fixtures run, not
    yet during conftest's own module-level import. Unset outside -n, so a
    plain sequential run keeps using the original shared ./test.db."""
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    db_path = f"./test_{worker}.db" if worker else "./test.db"
    return f"sqlite+aiosqlite:///{db_path}"


@pytest.fixture(scope="session", autouse=True)
def configure_db() -> None:
    """Initialise the DB module with the test SQLite database once per session."""
    init_db(_test_db_url())


@pytest.fixture()
async def db():
    engine = create_async_engine(_test_db_url(), connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        await seed_fixture_data(session)
        # Pre-compute scores so HTTP endpoint tests don't get empty results.
        # The lifespan skips recompute when scores already exist (count > 0),
        # avoiding a redundant second run per test.
        await recompute_all_scores(session)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The auth rate limiter is in-process global state — reset it between
    tests so one test's request volume can't trip another's limit."""
    from app.services.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture()
async def client(db):
    engine = create_async_engine(_test_db_url(), connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()
