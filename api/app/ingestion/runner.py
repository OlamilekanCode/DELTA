import sys
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_engine, get_factory, init_db
from app.models.asset import Asset
from app.models.price import DailyPrice
from app.providers.base import PriceRow, ProviderProtocol
from app.providers.coingecko import CoinGeckoProvider
from app.providers.fixtures import FIXTURE_ASSETS, FixtureProvider
from app.providers.marketstack import MarketstackProvider


def _get_provider(asset_type: str, settings: Settings) -> ProviderProtocol:
    """
    Returns FixtureProvider when USE_DEMO_DATA is true.
    When USE_DEMO_DATA is false, requires both API keys and fails clearly if either is absent.
    Never mixes fixture and real providers within one ingestion run.
    """
    if settings.use_demo_data:
        return FixtureProvider()

    if asset_type == "stock":
        if not settings.marketstack_api_key:
            print("ERROR: MARKETSTACK_API_KEY is required when USE_DEMO_DATA=false", file=sys.stderr)
            sys.exit(1)
        return MarketstackProvider(settings.marketstack_api_key)

    # crypto
    if not settings.coingecko_api_key:
        print("ERROR: COINGECKO_API_KEY is required when USE_DEMO_DATA=false", file=sys.stderr)
        sys.exit(1)
    return CoinGeckoProvider(settings.coingecko_api_key)


async def _upsert_prices(
    db: AsyncSession, asset_id: int, rows: list[PriceRow], is_demo: bool
) -> int:
    if not rows:
        return 0
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
    # CoinGecko expects coingecko_id; Marketstack and FixtureProvider expect symbol.
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
    """Called by lifespan when USE_DEMO_DATA=true. Seeds catalogue + fixture prices."""
    result = await db.execute(select(Asset).limit(1))
    if result.scalar():
        return  # Already seeded

    provider = FixtureProvider()
    for asset_data in FIXTURE_ASSETS:
        asset = Asset(
            symbol=asset_data["symbol"],
            name=asset_data["name"],
            asset_type=asset_data["asset_type"],
            category=asset_data["category"],
            coingecko_id=asset_data.get("coingecko_id"),
            updated_at=datetime.now(UTC),
        )
        db.add(asset)
        await db.flush()
        rows = await provider.fetch_ohlcv(asset.symbol, 90)
        await _upsert_prices(db, asset.id, rows, is_demo=True)

    await db.commit()


async def main() -> None:
    settings = get_settings()
    init_db(settings.database_url)
    try:
        async with get_factory()() as db:
            await seed_asset_catalogue(db)
            assets_result = await db.execute(select(Asset))
            assets = list(assets_result.scalars().all())
            for asset in assets:
                provider = _get_provider(asset.asset_type, settings)
                n = await ingest_asset(db, asset, provider)
                mode = "demo" if settings.use_demo_data else "real"
                print(f"[{mode}] {asset.symbol}: {n} new rows")
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
