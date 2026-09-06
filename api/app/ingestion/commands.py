"""
Explicit idempotent ingestion commands.

Usage:
    python -m app.ingestion.commands backfill
    python -m app.ingestion.commands refresh-crypto-quotes
    python -m app.ingestion.commands refresh-stock-eod
    python -m app.ingestion.commands recompute-scores
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import get_settings
from app.database import get_engine, get_factory, init_db
from app.ingestion.runner import ingest_asset, seed_asset_catalogue
from app.models.asset import Asset
from app.providers.coingecko import CoinGeckoProvider
from app.providers.marketstack import MarketstackProvider
from app.services.scoring import recompute_all_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


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
        result = await db.execute(select(Asset))
        assets = list(result.scalars().all())
        for asset in assets:
            provider = cg if asset.asset_type == "crypto" else ms
            n = await ingest_asset(db, asset, provider)
            log.info("%s: %d rows upserted", asset.symbol, n)


async def cmd_refresh_crypto_quotes() -> None:
    """Batch-refresh current prices for all 30 crypto assets from CoinGecko /coins/markets."""
    settings = get_settings()
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live quote refresh")
        return

    if not settings.coingecko_api_key:
        log.error("COINGECKO_API_KEY required")
        sys.exit(1)

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

        quotes = await cg.fetch_quotes_batch(cg_ids)
        log.info("Fetched %d quotes", len(quotes))

        from app.models.quote import AssetQuote

        symbol_to_asset = {a.symbol: a for a in crypto_assets}
        now = datetime.now(UTC)

        for q in quotes:
            asset = symbol_to_asset.get(q.symbol)
            if not asset:
                continue
            existing = await db.execute(
                select(AssetQuote).where(AssetQuote.asset_id == asset.id)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.price_usd = q.price_usd
                row.market_cap_usd = q.market_cap_usd
                row.volume_24h_usd = q.volume_24h_usd
                row.change_24h_pct = q.change_24h_pct
                row.ts = now
                row.is_demo = False
            else:
                db.add(AssetQuote(
                    asset_id=asset.id,
                    price_usd=q.price_usd,
                    market_cap_usd=q.market_cap_usd,
                    volume_24h_usd=q.volume_24h_usd,
                    change_24h_pct=q.change_24h_pct,
                    ts=now,
                    provider="coingecko",
                    is_demo=False,
                ))
        await db.commit()
        log.info("Quotes persisted")


async def cmd_refresh_stock_eod() -> None:
    """Refresh EOD prices for all 8 stocks (weekdays only)."""
    from datetime import date

    settings = get_settings()
    if settings.use_demo_data:
        log.info("USE_DEMO_DATA=true — skipping live stock refresh")
        return

    if not settings.marketstack_api_key:
        log.error("MARKETSTACK_API_KEY required")
        sys.exit(1)

    today = date.today()
    if today.weekday() >= 5:  # Sat=5, Sun=6
        log.info("Weekend — skipping stock EOD refresh")
        return

    ms = MarketstackProvider(settings.marketstack_api_key)
    async with get_factory()() as db:
        result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
        stocks = result.scalars().all()
        for stock in stocks:
            n = await ingest_asset(db, stock, ms)
            log.info("%s: %d rows upserted", stock.symbol, n)


async def cmd_recompute_scores() -> None:
    """Precompute and store Exposure Scores for all stock × crypto pairs."""
    async with get_factory()() as db:
        n = await recompute_all_scores(db)
        log.info("Stored %d exposure scores", n)


async def _run(cmd: str) -> None:
    settings = get_settings()
    init_db(settings.database_url)
    try:
        if cmd == "backfill":
            await cmd_backfill()
        elif cmd == "refresh-crypto-quotes":
            await cmd_refresh_crypto_quotes()
        elif cmd == "refresh-stock-eod":
            await cmd_refresh_stock_eod()
        elif cmd == "recompute-scores":
            await cmd_recompute_scores()
        else:
            log.error("Unknown command: %s", cmd)
            sys.exit(1)
    finally:
        await get_engine().dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="DELTA ingestion commands")
    parser.add_argument(
        "command",
        choices=["backfill", "refresh-crypto-quotes", "refresh-stock-eod", "recompute-scores"],
        help="Command to run",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.command))


if __name__ == "__main__":
    main()
