"""
Explicit idempotent ingestion commands.

Usage:
    python -m app.ingestion.commands backfill
    python -m app.ingestion.commands refresh-crypto-quotes
    python -m app.ingestion.commands refresh-stock-eod
    python -m app.ingestion.commands refresh-crypto-history
    python -m app.ingestion.commands recompute-scores
    python -m app.ingestion.commands refresh-all
"""

import argparse
import asyncio
import logging
import os
import sys
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database import get_engine, get_factory, init_db
from app.ingestion.runner import _upsert_quote, ingest_asset, seed_asset_catalogue
from app.models.asset import Asset
from app.providers.coingecko import CoinGeckoProvider
from app.providers.marketstack import MarketstackProvider
from app.services.scoring import recompute_all_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _try_lock(command_name: str) -> bool:
    """Acquire a PID-file lock for CLI use. Returns False if another instance is running."""
    lock_path = Path(tempfile.gettempdir()) / f"delta_{command_name}.lock"
    if lock_path.exists():
        try:
            existing_pid = int(lock_path.read_text().strip())
            os.kill(existing_pid, 0)  # raises OSError if process is gone
            return False
        except (ValueError, OSError):
            pass  # stale lock
    lock_path.write_text(str(os.getpid()))
    import atexit
    atexit.register(lambda: lock_path.unlink(missing_ok=True))
    return True


def _require_keys(settings) -> None:
    missing = [
        k for k, v in [
            ("MARKETSTACK_API_KEY", settings.marketstack_api_key),
            ("COINGECKO_API_KEY", settings.coingecko_api_key),
        ] if not v
    ]
    if missing:
        for k in missing:
            log.error("ERROR: %s is required when USE_DEMO_DATA=false", k)
        sys.exit(1)


async def cmd_backfill() -> None:
    """Initial 90-day historical backfill for all assets."""
    settings = get_settings()
    if settings.use_demo_data:
        from app.ingestion.runner import seed_fixture_data
        async with get_factory()() as db:
            await seed_fixture_data(db)
            log.info("Fixture backfill complete")
        return

    _require_keys(settings)
    cg = CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)
    ms = MarketstackProvider(settings.marketstack_api_key)

    async with get_factory()() as db:
        await seed_asset_catalogue(db)
        result = await db.execute(select(Asset.id, Asset.symbol, Asset.asset_type))
        asset_rows = result.all()  # plain tuples — safe after session close

    for asset_id, symbol, asset_type in asset_rows:
        provider = cg if asset_type == "crypto" else ms
        try:
            async with get_factory()() as asset_db:
                asset = await asset_db.get(Asset, asset_id)
                n = await ingest_asset(asset_db, asset, provider)
                log.info("%s: %d rows upserted", symbol, n)
        except Exception:
            log.exception("Failed to ingest %s — skipping, existing data preserved", symbol)


async def cmd_refresh_crypto_quotes() -> None:
    """Batch-refresh current prices for all 30 crypto assets from CoinGecko /coins/markets."""
    settings = get_settings()
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live quote refresh")
        return

    if not settings.coingecko_api_key:
        raise RuntimeError("COINGECKO_API_KEY is required when USE_DEMO_DATA=false")

    cg = CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)

    async with get_factory()() as db:
        result = await db.execute(
            select(Asset).where(Asset.asset_type == "crypto", Asset.coingecko_id.is_not(None))
        )
        crypto_assets = result.scalars().all()
        cg_ids = [a.coingecko_id for a in crypto_assets if a.coingecko_id]
        if not cg_ids:
            log.info("No crypto assets found")
            return

        try:
            quotes = await cg.fetch_quotes_batch(cg_ids)
        except Exception:
            log.exception("Provider error — existing quote data preserved")
            return

        log.info("Fetched %d quotes", len(quotes))
        symbol_to_asset = {a.symbol: a for a in crypto_assets}
        now = datetime.now(UTC)

        for q in quotes:
            asset = symbol_to_asset.get(q.symbol)
            if not asset:
                continue
            await _upsert_quote(
                db=db,
                asset_id=asset.id,
                price_usd=q.price_usd,
                market_cap_usd=q.market_cap_usd,
                volume_24h_usd=q.volume_24h_usd,
                change_24h_pct=q.change_24h_pct,
                provider="coingecko",
                is_demo=False,
                ts=now,
            )

        await db.commit()
        log.info("Quotes persisted")


async def cmd_refresh_stock_eod(skip_weekends: bool = True) -> None:
    """Refresh EOD prices for all 8 stocks."""
    settings = get_settings()
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live stock refresh")
        return

    if not settings.marketstack_api_key:
        raise RuntimeError("MARKETSTACK_API_KEY is required when USE_DEMO_DATA=false")

    if skip_weekends and date.today().weekday() >= 5:
        log.info("Weekend — skipping stock EOD refresh")
        return

    ms = MarketstackProvider(settings.marketstack_api_key)
    async with get_factory()() as db:
        result = await db.execute(
            select(Asset.id, Asset.symbol).where(Asset.asset_type == "stock")
        )
        stock_rows = result.all()

    for asset_id, symbol in stock_rows:
        try:
            async with get_factory()() as asset_db:
                asset = await asset_db.get(Asset, asset_id)
                n = await ingest_asset(asset_db, asset, ms)
                log.info("%s: %d rows upserted", symbol, n)
        except Exception:
            log.exception("Failed to refresh %s — skipping, existing data preserved", symbol)


async def cmd_refresh_crypto_history() -> None:
    """Refresh 90-day OHLCV history for all 30 crypto assets from CoinGecko."""
    settings = get_settings()
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live crypto history refresh")
        return

    if not settings.coingecko_api_key:
        raise RuntimeError("COINGECKO_API_KEY is required when USE_DEMO_DATA=false")

    cg = CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)
    async with get_factory()() as db:
        result = await db.execute(
            select(Asset.id, Asset.symbol).where(Asset.asset_type == "crypto")
        )
        crypto_rows = result.all()

    for asset_id, symbol in crypto_rows:
        try:
            async with get_factory()() as asset_db:
                asset = await asset_db.get(Asset, asset_id)
                n = await ingest_asset(asset_db, asset, cg)
                log.info("%s: %d rows upserted", symbol, n)
        except Exception:
            log.exception("Failed to refresh %s — skipping, existing data preserved", symbol)


async def cmd_recompute_scores() -> None:
    """Precompute and store Exposure Scores for all stock × crypto pairs."""
    async with get_factory()() as db:
        n = await recompute_all_scores(db)
        log.info("Stored %d exposure scores", n)


async def cmd_refresh_all() -> None:
    """Refresh stock EOD history, crypto OHLCV history, then recompute scores.

    Runs all three operations in sequence.  Use this for the scheduled
    Tuesday/Friday data refresh.  The Cloudflare Cron schedule controls
    which days this runs — no weekday check is applied here.
    """
    await cmd_refresh_stock_eod(skip_weekends=False)
    await cmd_refresh_crypto_history()
    await cmd_recompute_scores()


_COMMANDS = {
    "backfill": cmd_backfill,
    "refresh-crypto-quotes": cmd_refresh_crypto_quotes,
    "refresh-stock-eod": cmd_refresh_stock_eod,
    "refresh-crypto-history": cmd_refresh_crypto_history,
    "recompute-scores": cmd_recompute_scores,
    "refresh-all": cmd_refresh_all,
}


async def _run(cmd: str) -> None:
    settings = get_settings()
    init_db(settings.database_url)
    try:
        await _COMMANDS[cmd]()
    finally:
        await get_engine().dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="DELTA ingestion commands")
    parser.add_argument(
        "command",
        choices=list(_COMMANDS),
        help="Command to run",
    )
    args = parser.parse_args()
    cmd = args.command
    if not _try_lock(cmd.replace("-", "_")):
        log.error("Command '%s' is already running. Exiting.", cmd)
        sys.exit(0)
    asyncio.run(_run(cmd))


if __name__ == "__main__":
    main()
