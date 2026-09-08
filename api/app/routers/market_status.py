from fastapi import APIRouter

from app.services.market_calendar import get_market_status

router = APIRouter()


@router.get("/market-status")
async def market_status() -> dict:
    status = get_market_status()
    return {
        "is_open": status.is_open,
        "timezone": status.timezone,
        "last_close": status.last_close.isoformat(),
        "next_open": status.next_open.isoformat(),
        "current_bucket": status.current_bucket.isoformat() if status.current_bucket else None,
        "status_reason": status.status_reason,
    }
