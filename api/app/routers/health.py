from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import get_settings
from app.database import get_factory
from app.services.purchase_verification import purchase_verification_status

router = APIRouter()


@router.get("/health")
async def health(response: Response) -> dict:
    """Combined liveness/readiness check. A failed database check must
    never report back as a healthy 200 — Render's health check (and any
    other monitor) needs a real non-2xx to detect and act on an unreachable
    database, not `status: ok` with the failure buried in a nested field.

    `purchase_verification` is included so "env vars are set but nobody has
    registered a RouterAdapter yet" is visible on a plain health check
    rather than only discoverable by submitting a real transaction hash and
    watching it fail deep in the pipeline."""
    settings = get_settings()
    db_status = "ok"
    try:
        factory = get_factory()
        async with factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    if db_status != "ok":
        response.status_code = 503

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "demo_mode": settings.use_demo_data,
        "purchase_verification": purchase_verification_status(),
    }
