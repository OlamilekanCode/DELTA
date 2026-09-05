from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import get_factory

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    db_status = "ok"
    try:
        factory = get_factory()
        async with factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    return {
        "status": "ok",
        "db": db_status,
        "demo_mode": settings.use_demo_data,
    }
