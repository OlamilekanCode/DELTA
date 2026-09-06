"""Protected cron endpoints for scheduled data refresh.

Intended to be called by Cloudflare Cron (or any HTTPS scheduler).
Every request must carry the correct X-Cron-Secret header.

Recommended Cloudflare Cron schedule:
  POST /api/v1/cron/refresh-crypto-quotes      every 5 minutes
  POST /api/v1/cron/refresh-history-and-scores  every Tuesday and Friday
"""

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.ingestion.commands import (
    cmd_recompute_scores,
    cmd_refresh_crypto_history,
    cmd_refresh_crypto_quotes,
    cmd_refresh_stock_eod,
)
from app.ingestion.lock import JobAlreadyRunningError, advisory_lock

router = APIRouter()


def _check_secret(x_cron_secret: str) -> None:
    settings = get_settings()
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/cron/refresh-crypto-quotes")
async def trigger_refresh_crypto_quotes(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh current crypto quote prices from CoinGecko.

    Runs every 5 minutes.  Idempotent — if another instance is already
    running the same job the request returns immediately with skipped=True.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock("refresh-crypto-quotes"):
            await cmd_refresh_crypto_quotes()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    return {"ok": True, "command": "refresh-crypto-quotes"}


@router.post("/cron/refresh-history-and-scores")
async def trigger_refresh_history_and_scores(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh stock EOD + crypto OHLCV history, then recompute Exposure Scores.

    Runs every Tuesday and Friday (controlled by the Cloudflare Cron schedule).
    The endpoint itself does not enforce a weekday restriction.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock("refresh-history-and-scores"):
            await cmd_refresh_stock_eod(skip_weekends=False)
            await cmd_refresh_crypto_history()
            await cmd_recompute_scores()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    return {"ok": True, "command": "refresh-history-and-scores"}
