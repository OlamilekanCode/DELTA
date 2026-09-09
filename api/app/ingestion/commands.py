"""
Explicit idempotent ingestion commands.

Usage:
    python -m app.ingestion.commands backfill
    python -m app.ingestion.commands refresh-crypto-quotes
    python -m app.ingestion.commands refresh-stock-eod
    python -m app.ingestion.commands refresh-crypto-history
    python -m app.ingestion.commands recompute-scores
    python -m app.ingestion.commands refresh-intraday
    python -m app.ingestion.commands refresh-all
    python -m app.ingestion.commands cleanup-old-data
"""

import argparse
import asyncio
import logging
import os
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import get_engine, get_factory, init_db
from app.ingestion.errors import MissingProviderKeysError
from app.ingestion.runner import _upsert_quote, ingest_asset, seed_asset_catalogue
from app.models.asset import Asset
from app.models.crypto_observation import CryptoQuoteObservation
from app.providers.coingecko import CoinGeckoProvider
from app.providers.marketstack import MarketstackProvider
from app.services.scoring import recompute_all_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _try_lock(command_name: str) -> bool:
    """Acquire a PID-file lock for CLI use. Returns False if another instance is running."""
    lock_path = Path(tempfile.gettempdir()) / f"synthex_{command_name}.lock"
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
        message = f"Missing required provider key(s): {', '.join(missing)} (required when USE_DEMO_DATA=false)"
        log.error(message)
        raise MissingProviderKeysError(message)


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


async def cmd_refresh_crypto_quotes() -> dict:
    """Batch-refresh current prices for every crypto asset in ONE CoinGecko
    /coins/markets call, and persist a timestamped observation per asset —
    these observations are what the 30-minute intraday job later buckets
    into candles, so no separate per-asset intraday provider call is needed.
    """
    settings = get_settings()
    counts = {"requested": 0, "succeeded": 0, "skipped": 0, "failed": 0}
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live quote refresh")
        counts["skipped"] = 1
        return counts

    if not settings.coingecko_api_key:
        raise RuntimeError("COINGECKO_API_KEY is required when USE_DEMO_DATA=false")

    cg = CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)

    async with get_factory()() as db:
        result = await db.execute(
            select(Asset).where(Asset.asset_type == "crypto", Asset.coingecko_id.is_not(None))
        )
        crypto_assets = result.scalars().all()
        cg_ids = [a.coingecko_id for a in crypto_assets if a.coingecko_id]
        counts["requested"] = len(cg_ids)
        if not cg_ids:
            log.info("No crypto assets found")
            return counts

        try:
            quotes = await cg.fetch_quotes_batch(cg_ids)
        except Exception:
            log.exception("Provider error — existing quote data preserved")
            counts["failed"] = counts["requested"]
            return counts

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
            db.add(CryptoQuoteObservation(asset_id=asset.id, ts=now, price_usd=q.price_usd, is_demo=False))
            counts["succeeded"] += 1

        counts["failed"] = max(0, counts["requested"] - counts["succeeded"])
        await db.commit()
        log.info("Quotes persisted: %d/%d", counts["succeeded"], counts["requested"])
        return counts


async def cmd_refresh_stock_eod(skip_weekends: bool = True) -> dict:
    """Refresh EOD prices for every stock."""
    settings = get_settings()
    counts = {"requested": 0, "succeeded": 0, "skipped": 0, "failed": 0, "records_written": 0}
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live stock refresh")
        counts["skipped"] = 1
        return counts

    if not settings.marketstack_api_key:
        raise RuntimeError("MARKETSTACK_API_KEY is required when USE_DEMO_DATA=false")

    if skip_weekends and date.today().weekday() >= 5:
        log.info("Weekend — skipping stock EOD refresh")
        counts["skipped"] = 1
        return counts

    ms = MarketstackProvider(settings.marketstack_api_key)
    async with get_factory()() as db:
        result = await db.execute(
            select(Asset.id, Asset.symbol).where(Asset.asset_type == "stock")
        )
        stock_rows = result.all()

    counts["requested"] = len(stock_rows)
    for asset_id, symbol in stock_rows:
        try:
            async with get_factory()() as asset_db:
                asset = await asset_db.get(Asset, asset_id)
                n = await ingest_asset(asset_db, asset, ms)
                log.info("%s: %d rows upserted", symbol, n)
                counts["succeeded"] += 1
                counts["records_written"] += n
        except Exception:
            log.exception("Failed to refresh %s — skipping, existing data preserved", symbol)
            counts["failed"] += 1
    return counts


async def cmd_refresh_crypto_history() -> dict:
    """Refresh 90-day OHLCV history for every crypto asset from CoinGecko."""
    settings = get_settings()
    counts = {"requested": 0, "succeeded": 0, "skipped": 0, "failed": 0, "records_written": 0}
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live crypto history refresh")
        counts["skipped"] = 1
        return counts

    if not settings.coingecko_api_key:
        raise RuntimeError("COINGECKO_API_KEY is required when USE_DEMO_DATA=false")

    cg = CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)
    async with get_factory()() as db:
        result = await db.execute(
            select(Asset.id, Asset.symbol).where(Asset.asset_type == "crypto")
        )
        crypto_rows = result.all()

    counts["requested"] = len(crypto_rows)
    for asset_id, symbol in crypto_rows:
        try:
            async with get_factory()() as asset_db:
                asset = await asset_db.get(Asset, asset_id)
                n = await ingest_asset(asset_db, asset, cg)
                log.info("%s: %d rows upserted", symbol, n)
                counts["succeeded"] += 1
                counts["records_written"] += n
        except Exception:
            log.exception("Failed to refresh %s — skipping, existing data preserved", symbol)
            counts["failed"] += 1
    return counts


async def cmd_refresh_intraday() -> dict:
    """Build the 30-minute intraday candle set, then recompute intraday
    Exposure Scores for every stock, atomically per stock.

    Crypto candles are built entirely from already-stored 5-minute
    `crypto_quote_observations` (see cmd_refresh_crypto_quotes) — this job
    makes ZERO CoinGecko calls. Stock candles come from ONE batched
    Marketstack /intraday call for every stock symbol, never one call per
    symbol. Skipped while the US market is closed, except to finalize the
    last bucket of the session that just closed (within a grace window).
    """
    from app.services.intraday import (
        BUCKET_MINUTES,
        IntradayObservation,
        build_30min_candles,
        ingest_intraday_candles,
        recompute_intraday_scores_for_stock,
    )
    from app.services.market_calendar import get_market_status

    settings = get_settings()
    counts = {"requested": 0, "succeeded": 0, "skipped": 0, "failed": 0}
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — intraday fixtures are seeded at startup, nothing to refresh")
        counts["skipped"] = 1
        return counts

    now = datetime.now(UTC)
    status = get_market_status(now)
    closing_grace = timedelta(minutes=35)
    is_final_closing_bucket = not status.is_open and (now - status.last_close) <= closing_grace
    if not status.is_open and not is_final_closing_bucket:
        log.info("US market closed — skipping intraday refresh")
        counts["skipped"] = 1
        return counts

    _require_keys(settings)
    ms = MarketstackProvider(settings.marketstack_api_key)

    async with get_factory()() as db:
        stocks_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
        stocks = list(stocks_result.scalars().all())
        crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
        crypto_assets = list(crypto_result.scalars().all())

    counts["requested"] = len(stocks) + len(crypto_assets)

    # Stocks: one batched Marketstack call for every symbol.
    counts["marketstack_failed"] = False
    try:
        candles_by_symbol = await ms.fetch_intraday_candles_batch([s.symbol for s in stocks])
    except Exception:
        log.exception("Marketstack batch intraday call failed — existing data preserved")
        candles_by_symbol = {}
        counts["failed"] += len(stocks)
        counts["marketstack_failed"] = True

    if candles_by_symbol:
        async with get_factory()() as db:
            for stock in stocks:
                candles = [
                    c for c in candles_by_symbol.get(stock.symbol, [])
                    if c.bucket_ts + timedelta(minutes=BUCKET_MINUTES) <= now
                ]
                if not candles:
                    counts["skipped"] += 1
                    continue
                n = await ingest_intraday_candles(db, stock.id, candles, provider="marketstack", is_demo=False)
                counts["succeeded"] += 1
                log.info("%s: %d intraday candles upserted", stock.symbol, n)
            await db.commit()

    # Crypto: build candles purely from stored 5-minute observations — no provider calls.
    lookback = now - timedelta(hours=2)
    async with get_factory()() as db:
        for asset in crypto_assets:
            try:
                obs_result = await db.execute(
                    select(CryptoQuoteObservation.ts, CryptoQuoteObservation.price_usd).where(
                        CryptoQuoteObservation.asset_id == asset.id,
                        CryptoQuoteObservation.ts >= lookback,
                    )
                )
                observations = [
                    IntradayObservation(
                        ts=r.ts if r.ts.tzinfo is not None else r.ts.replace(tzinfo=UTC),
                        price=r.price_usd,
                    )
                    for r in obs_result.all()
                ]
                all_candles = build_30min_candles(observations)
                # Never persist the current/in-progress bucket.
                completed = [
                    c for c in all_candles if c.bucket_ts + timedelta(minutes=BUCKET_MINUTES) <= now
                ]
                if not completed:
                    counts["skipped"] += 1
                    continue
                n = await ingest_intraday_candles(db, asset.id, completed, provider="coingecko", is_demo=False)
                counts["succeeded"] += 1
                log.info("%s: %d intraday candles upserted", asset.symbol, n)
            except Exception:
                log.exception("Failed to build intraday candles for %s — existing data preserved", asset.symbol)
                counts["failed"] += 1
        await db.commit()

    counts["score_pairs_recomputed"] = 0
    counts["score_stocks_recomputed"] = 0
    counts["score_stocks_failed"] = 0
    async with get_factory()() as db:
        stocks_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
        stocks = stocks_result.scalars().all()
        crypto_result = await db.execute(select(Asset).where(Asset.asset_type == "crypto"))
        crypto_assets = crypto_result.scalars().all()
        for stock in stocks:
            try:
                results, _ = await recompute_intraday_scores_for_stock(db, stock, crypto_assets)
                # Only count a stock as "recomputed" when it actually had
                # candle data to score against — a stock with zero candles
                # (e.g. Marketstack failed completely) trivially returns
                # `[]` without raising, and that must not be mistaken for a
                # real recomputation when checking whether the job as a
                # whole produced anything.
                if results:
                    counts["score_stocks_recomputed"] += 1
                    counts["score_pairs_recomputed"] += sum(1 for r in results if not r.collecting_data)
            except Exception:
                log.exception("Failed to recompute intraday scores for %s", stock.symbol)
                counts["score_stocks_failed"] += 1

    return counts


_INTRADAY_RETENTION_DAYS = 90
_CRYPTO_OBSERVATION_RETENTION_DAYS = 7


async def cmd_cleanup_old_data() -> dict:
    """Idempotently delete raw 5-min crypto observations (7-day retention),
    30-min intraday candles (90-day retention), and expired SIWE
    nonces/sessions. Daily (session-aligned) data is kept long-term and never
    deleted here. Safe to run repeatedly — deleting already-deleted rows is a
    no-op. Folded into the Tuesday/Friday historical maintenance job (see
    cron.py) so no fourth Cloudflare schedule is required."""
    from app.models.intraday_price import IntradayPrice
    from app.services.auth import cleanup_expired_auth_rows

    intraday_cutoff = datetime.now(UTC) - timedelta(days=_INTRADAY_RETENTION_DAYS)
    observation_cutoff = datetime.now(UTC) - timedelta(days=_CRYPTO_OBSERVATION_RETENTION_DAYS)
    async with get_factory()() as db:
        intraday_result = await db.execute(
            delete(IntradayPrice).where(IntradayPrice.bucket_ts < intraday_cutoff)
        )
        observation_result = await db.execute(
            delete(CryptoQuoteObservation).where(CryptoQuoteObservation.ts < observation_cutoff)
        )
        await db.commit()
        auth_counts = await cleanup_expired_auth_rows(db)
        log.info(
            "Deleted %d intraday_prices rows (>%dd), %d crypto_quote_observations rows (>%dd), "
            "%d expired nonces, %d expired sessions",
            intraday_result.rowcount, _INTRADAY_RETENTION_DAYS,
            observation_result.rowcount, _CRYPTO_OBSERVATION_RETENTION_DAYS,
            auth_counts["nonces_deleted"], auth_counts["sessions_deleted"],
        )
        return {
            "intraday_prices_deleted": intraday_result.rowcount,
            "crypto_quote_observations_deleted": observation_result.rowcount,
            **auth_counts,
        }


async def cmd_recompute_scores() -> int:
    """Precompute and store Exposure Scores for all stock × crypto pairs."""
    async with get_factory()() as db:
        n = await recompute_all_scores(db)
        log.info("Stored %d exposure scores", n)
        return n


async def cmd_refresh_all() -> dict:
    """Refresh stock EOD history, crypto OHLCV history, recompute scores, and
    run retention cleanup — the full Tuesday/Friday historical maintenance
    job. Cleanup is folded in here so no fourth Cloudflare schedule is
    needed. The Cloudflare Cron schedule controls which days this runs — no
    weekday check is applied here.
    """
    stock_counts = await cmd_refresh_stock_eod(skip_weekends=False)
    crypto_counts = await cmd_refresh_crypto_history()
    scores_written = await cmd_recompute_scores()
    cleanup_counts = await cmd_cleanup_old_data()
    return {
        "stock_eod": stock_counts,
        "crypto_history": crypto_counts,
        "scores_written": scores_written,
        "cleanup": cleanup_counts,
    }


_COMMANDS = {
    "backfill": cmd_backfill,
    "refresh-crypto-quotes": cmd_refresh_crypto_quotes,
    "refresh-stock-eod": cmd_refresh_stock_eod,
    "refresh-crypto-history": cmd_refresh_crypto_history,
    "recompute-scores": cmd_recompute_scores,
    "refresh-intraday": cmd_refresh_intraday,
    "refresh-all": cmd_refresh_all,
    "cleanup-old-data": cmd_cleanup_old_data,
}


async def _run(cmd: str) -> None:
    settings = get_settings()
    init_db(settings.database_url)
    try:
        await _COMMANDS[cmd]()
    finally:
        await get_engine().dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic Exposure ingestion commands")
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
    try:
        asyncio.run(_run(cmd))
    except MissingProviderKeysError:
        sys.exit(1)


if __name__ == "__main__":
    main()
