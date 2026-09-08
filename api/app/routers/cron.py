"""Protected cron endpoints for scheduled data refresh.

Intended to be called by a Cloudflare Worker (see cloudflare/src/worker.js).
Every request must carry the correct X-Cron-Secret header.

Recommended schedule (configured in cloudflare/wrangler.toml):
  POST /api/v1/cron/refresh-crypto-quotes       every 5 minutes
  POST /api/v1/cron/refresh-history-and-scores  every Tuesday and Friday
  POST /api/v1/cron/refresh-intraday            every 30 minutes (backend
                                                 decides whether a bucket is
                                                 actually due and whether the
                                                 market is open)

The quote and history endpoints share the "ingestion" advisory lock so they
can never overlap. Intraday refresh uses its own distinct lock ("intraday")
so it isn't serialized behind the other two.
"""

import hmac

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.ingestion.commands import (
    cmd_recompute_scores,
    cmd_refresh_crypto_history,
    cmd_refresh_crypto_quotes,
    cmd_refresh_intraday,
    cmd_refresh_stock_eod,
)
from app.ingestion.lock import JobAlreadyRunningError, advisory_lock

router = APIRouter()

_LOCK_NAME = "ingestion"
_INTRADAY_LOCK_NAME = "intraday"


def _check_secret(x_cron_secret: str) -> None:
    settings = get_settings()
    secret = settings.cron_secret or ""
    if not secret or not hmac.compare_digest(x_cron_secret, secret):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/cron/refresh-crypto-quotes")
async def trigger_refresh_crypto_quotes(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh current crypto quote prices from CoinGecko.

    Runs every 5 minutes.  Shares the global ingestion lock with the
    history endpoint so the two jobs cannot run concurrently.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock(_LOCK_NAME):
            await cmd_refresh_crypto_quotes()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "command": "refresh-crypto-quotes"}


@router.post("/cron/refresh-history-and-scores")
async def trigger_refresh_history_and_scores(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh stock EOD + crypto OHLCV history, then recompute Exposure Scores.

    Runs every Tuesday and Friday (controlled by the Cloudflare Cron schedule).
    Shares the global ingestion lock so it cannot overlap with the quote refresh.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock(_LOCK_NAME):
            await cmd_refresh_stock_eod(skip_weekends=False)
            await cmd_refresh_crypto_history()
            await cmd_recompute_scores()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "command": "refresh-history-and-scores"}


@router.post("/cron/refresh-intraday")
async def trigger_refresh_intraday(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh 30-min intraday candles and recompute intraday Exposure Scores.

    Runs every 30 minutes; cmd_refresh_intraday() itself decides whether the
    US market is open (skipping otherwise) and whether demo mode applies.
    Uses its own advisory lock so it never waits behind the quote/history jobs.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock(_INTRADAY_LOCK_NAME):
            await cmd_refresh_intraday()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "command": "refresh-intraday"}
