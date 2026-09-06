import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_engine, get_factory, init_db
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.models.quote import AssetQuote
from app.providers.base import PriceRow, ProviderProtocol
from app.providers.coingecko import CoinGeckoProvider
from app.providers.fixtures import (
    _SYMBOL_DATA,
    FIXTURE_ASSETS,
    FixtureProvider,
    _fixture_change_pct,
)
from app.providers.marketstack import MarketstackProvider

log = logging.getLogger(__name__)


def _get_provider(asset_type: str, settings: Settings) -> ProviderProtocol:
    if settings.use_demo_data:
        return FixtureProvider()
    if asset_type == "stock":
        if not settings.marketstack_api_key:
            log.error("MARKETSTACK_API_KEY is required when USE_DEMO_DATA=false")
            sys.exit(1)
        return MarketstackProvider(settings.marketstack_api_key)
    if not settings.coingecko_api_key:
        log.error("COINGECKO_API_KEY is required when USE_DEMO_DATA=false")
        sys.exit(1)
    return CoinGeckoProvider(settings.coingecko_api_key, settings.coingecko_api_type)


async def _upsert_prices(
    db: AsyncSession, asset_id: int, rows: list[PriceRow], is_demo: bool
) -> int:
    if not rows:
        return 0
    # Remove rows from the opposite source so an asset never holds a mix.
    await db.execute(
        delete(DailyPrice).where(
            DailyPrice.asset_id == asset_id,
            DailyPrice.is_demo == (not is_demo),
        )
    )
    dates = [r.date for r in rows]
    result = await db.execute(
        select(DailyPrice).where(
            DailyPrice.asset_id == asset_id,
            DailyPrice.date.in_(dates),
        )
    )
    existing_by_date = {row.date: row for row in result.scalars().all()}
    inserted = 0
    for r in rows:
        if r.date in existing_by_date:
            rec = existing_by_date[r.date]
            rec.close = r.close
            rec.volume = r.volume
            rec.is_demo = is_demo
        else:
            db.add(
                DailyPrice(
                    asset_id=asset_id,
                    date=r.date,
                    close=r.close,
                    volume=r.volume,
                    is_demo=is_demo,
                )
            )
            inserted += 1
    return inserted


async def _upsert_quote(
    db: AsyncSession,
    asset_id: int,
    price_usd: float,
    market_cap_usd: float | None,
    volume_24h_usd: float | None,
    change_24h_pct: float | None,
    provider: str,
    is_demo: bool,
    ts: datetime,
) -> None:
    """Insert or update the single quote row for an asset.

    On PostgreSQL: uses INSERT … ON CONFLICT DO UPDATE for atomic, concurrency-safe
    upsert.  The unique constraint on asset_id (added by migration 0004) is the
    conflict target.

    On SQLite (development / tests): falls back to SELECT-then-UPDATE-or-INSERT.
    SQLite is single-process so there is no concurrent-write risk.
    """
    dialect = get_engine().dialect.name

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        fields = dict(
            price_usd=price_usd,
            market_cap_usd=market_cap_usd,
            volume_24h_usd=volume_24h_usd,
            change_24h_pct=change_24h_pct,
            provider=provider,
            is_demo=is_demo,
            ts=ts,
        )
        stmt = pg_insert(AssetQuote).values(asset_id=asset_id, **fields)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id"],
            set_=fields,
        )
        await db.execute(stmt)
        return

    # SQLite path
    result = await db.execute(
        select(AssetQuote).where(AssetQuote.asset_id == asset_id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.price_usd = price_usd
        row.market_cap_usd = market_cap_usd
        row.volume_24h_usd = volume_24h_usd
        row.change_24h_pct = change_24h_pct
        row.provider = provider
        row.is_demo = is_demo
        row.ts = ts
    else:
        db.add(AssetQuote(
            asset_id=asset_id,
            price_usd=price_usd,
            market_cap_usd=market_cap_usd,
            volume_24h_usd=volume_24h_usd,
            change_24h_pct=change_24h_pct,
            provider=provider,
            is_demo=is_demo,
            ts=ts,
        ))


async def seed_asset_catalogue(db: AsyncSession) -> None:
    """Upsert asset catalogue rows without touching price data."""
    for asset_data in FIXTURE_ASSETS:
        result = await db.execute(select(Asset).where(Asset.symbol == asset_data["symbol"]))
        if result.scalar_one_or_none():
            continue
        db.add(
            Asset(
                symbol=asset_data["symbol"],
                name=asset_data["name"],
                asset_type=asset_data["asset_type"],
                category=asset_data["category"],
                coingecko_id=asset_data.get("coingecko_id"),
                updated_at=datetime.now(UTC),
            )
        )
    await db.commit()


async def ingest_asset(
    db: AsyncSession, asset: Asset, provider: ProviderProtocol
) -> int:
    key = (
        asset.coingecko_id
        if isinstance(provider, CoinGeckoProvider) and asset.coingecko_id
        else asset.symbol
    )
    is_demo = isinstance(provider, FixtureProvider)
    rows: list[PriceRow] = await provider.fetch_ohlcv(key, 90)
    n = await _upsert_prices(db, asset.id, rows, is_demo=is_demo)
    asset.updated_at = datetime.now(UTC)
    await db.commit()
    return n


async def seed_fixture_data(db: AsyncSession) -> None:
    """Seeds catalogue + fixture prices + crypto quotes idempotently."""
    provider = FixtureProvider()
    now = datetime.now(UTC)

    for asset_data in FIXTURE_ASSETS:
        result = await db.execute(select(Asset).where(Asset.symbol == asset_data["symbol"]))
        asset = result.scalar_one_or_none()
        if not asset:
            asset = Asset(
                symbol=asset_data["symbol"],
                name=asset_data["name"],
                asset_type=asset_data["asset_type"],
                category=asset_data["category"],
                coingecko_id=asset_data.get("coingecko_id"),
                updated_at=now,
            )
            db.add(asset)
            await db.flush()

        rows = await provider.fetch_ohlcv(asset.symbol, 90)
        await _upsert_prices(db, asset.id, rows, is_demo=True)

        if asset.asset_type == "crypto":
            prices = _SYMBOL_DATA.get(asset.symbol, [])
            if prices:
                price = float(prices[-1])
                await _upsert_quote(
                    db=db,
                    asset_id=asset.id,
                    price_usd=price,
                    market_cap_usd=round(price * 18_000_000, 2),
                    volume_24h_usd=round(price * 1_500_000, 2),
                    change_24h_pct=_fixture_change_pct(asset.symbol),
                    provider="fixture",
                    is_demo=True,
                    ts=now,
                )

    await db.commit()


async def main() -> None:
    settings = get_settings()
    if not settings.use_demo_data:
        missing = [
            k for k, v in [
                ("MARKETSTACK_API_KEY", settings.marketstack_api_key),
                ("COINGECKO_API_KEY", settings.coingecko_api_key),
            ] if not v
        ]
        if missing:
            for key in missing:
                log.error("ERROR: %s is required when USE_DEMO_DATA=false", key)
            sys.exit(1)
    init_db(settings.database_url)
    try:
        async with get_factory()() as db:
            await seed_asset_catalogue(db)
            assets_result = await db.execute(select(Asset))
            assets = list(assets_result.scalars().all())
            for asset in assets:
                provider = _get_provider(asset.asset_type, settings)
                try:
                    n = await ingest_asset(db, asset, provider)
                    mode = "demo" if settings.use_demo_data else "real"
                    log.info("[%s] %s: %d new rows", mode, asset.symbol, n)
                except Exception:
                    log.exception("Failed to ingest %s — skipping, existing data preserved", asset.symbol)
                    await db.rollback()
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
