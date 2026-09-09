"""Protected cron endpoints for scheduled data refresh.

Intended to be called by a Cloudflare Worker (see cloudflare/src/worker.js).
Every request must carry the correct X-Cron-Secret header.

Three job types:
  POST /api/v1/cron/refresh-crypto-quotes       every 5 minutes
  POST /api/v1/cron/refresh-intraday            after each completed 30-min
                                                 market bucket (backend
                                                 decides whether a bucket is
                                                 actually due and whether the
                                                 market is open)
  POST /api/v1/cron/refresh-history-and-scores  Tuesday/Friday after close
                                                 (also runs retention cleanup)

The quote and history endpoints share the "ingestion" advisory lock so they
can never overlap. Intraday refresh uses its own distinct lock ("intraday")
so it isn't serialized behind the other two.

A genuine job failure (every provider call failed, or the job raised) returns
a non-2xx status — callers must never see HTTP 200 with ok:false for a real
failure, only for a deliberate no-op skip (already-running, market closed,
demo mode).
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


def _job_failed(counts: dict) -> bool:
    """A job is a genuine failure only when every attempted provider call
    failed — a partial success (some symbols failed, others succeeded) is
    reported as ok with the failure count visible, per the "existing data on
    failure" rule; a deliberate skip (demo mode, weekend, market closed) is
    never a failure."""
    return counts.get("requested", 0) > 0 and counts.get("succeeded", 0) == 0 and counts.get("skipped", 0) == 0


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
            counts = await cmd_refresh_crypto_quotes()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"refresh-crypto-quotes failed: {e}") from e

    if _job_failed(counts):
        raise HTTPException(status_code=502, detail={"command": "refresh-crypto-quotes", "counts": counts})
    return {"ok": True, "command": "refresh-crypto-quotes", "counts": counts}


@router.post("/cron/refresh-history-and-scores")
async def trigger_refresh_history_and_scores(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh stock EOD + crypto OHLCV history, recompute Exposure Scores,
    and run retention cleanup — the full Tuesday/Friday maintenance job.

    Shares the global ingestion lock so it cannot overlap with the quote refresh.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock(_LOCK_NAME):
            stock_counts = await cmd_refresh_stock_eod(skip_weekends=False)
            crypto_counts = await cmd_refresh_crypto_history()
            scores_written = await cmd_recompute_scores()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"refresh-history-and-scores failed: {e}") from e

    if _job_failed(stock_counts) and _job_failed(crypto_counts):
        raise HTTPException(
            status_code=502,
            detail={
                "command": "refresh-history-and-scores",
                "stock_eod": stock_counts,
                "crypto_history": crypto_counts,
            },
        )
    return {
        "ok": True,
        "command": "refresh-history-and-scores",
        "stock_eod": stock_counts,
        "crypto_history": crypto_counts,
        "scores_written": scores_written,
    }


@router.post("/cron/refresh-intraday")
async def trigger_refresh_intraday(
    x_cron_secret: str = Header(default=""),
) -> dict:
    """Refresh 30-min intraday candles and recompute intraday Exposure Scores.

    Runs after each completed 30-minute market bucket; cmd_refresh_intraday()
    itself decides whether the US market is open (skipping otherwise, except
    to finalize the final bucket right after close) and whether demo mode
    applies. Uses its own advisory lock so it never waits behind the
    quote/history jobs.
    """
    _check_secret(x_cron_secret)
    try:
        async with advisory_lock(_INTRADAY_LOCK_NAME):
            counts = await cmd_refresh_intraday()
    except JobAlreadyRunningError as e:
        return {"ok": False, "skipped": True, "message": str(e)}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"refresh-intraday failed: {e}") from e

    if _job_failed(counts):
        raise HTTPException(status_code=502, detail={"command": "refresh-intraday", "counts": counts})

    # Candle ingestion can look "successful" (crypto candles built fine from
    # already-stored observations) while the stock side is completely dead —
    # that must never be reported as success just because some candles
    # existed. Only checked when the job actually attempted real work
    # (skipped via demo-mode/market-closed never reaches this with
    # requested > 0).
    if counts.get("requested", 0) > 0 and (
        counts.get("marketstack_failed") or counts.get("score_stocks_recomputed", 0) == 0
    ):
        raise HTTPException(
            status_code=502,
            detail={"command": "refresh-intraday", "counts": counts, "reason": "no_intraday_scores_recomputed"},
        )
    return {"ok": True, "command": "refresh-intraday", "counts": counts}
