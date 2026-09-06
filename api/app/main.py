from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — register all ORM models with Base
from app.config import get_settings
from app.database import Base, get_engine, init_db
from app.routers import assets, correlation, cron, exposures, graphs, health


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    init_db(settings.database_url)

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.use_demo_data:
        from sqlalchemy import func, select

        from app.database import get_factory
        from app.ingestion.runner import seed_fixture_data
        from app.models.exposure_score import StoredExposureScore
        from app.services.scoring import recompute_all_scores

        async with get_factory()() as db:
            await seed_fixture_data(db)
            # Pre-compute scores on first run so HTTP routes never block.
            # Skip if scores already exist (e.g. test DB seeded by the db fixture).
            count_result = await db.execute(
                select(func.count()).select_from(StoredExposureScore)
            )
            if (count_result.scalar() or 0) == 0:
                await recompute_all_scores(db)

    yield

    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="DELTA — Synthetic Exposure API",
        version="3.0.0",
        description="Stock ↔ Crypto Exposure Layer",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    application.include_router(health.router, prefix="/api/v1")
    application.include_router(assets.router, prefix="/api/v1")
    application.include_router(correlation.router, prefix="/api/v1")
    application.include_router(exposures.router, prefix="/api/v1")
    application.include_router(graphs.router, prefix="/api/v1")
    application.include_router(cron.router, prefix="/api/v1")

    return application


app = create_app()
