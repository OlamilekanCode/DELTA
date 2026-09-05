from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.price import DailyPrice
from app.providers.base import PriceRow
from app.providers.fixtures import FIXTURE_ASSETS, FixtureProvider


async def _insert_new_prices(db: AsyncSession, asset_id: int, rows: list[PriceRow]) -> None:
    if not rows:
        return
    dates = [r.date for r in rows]
    result = await db.execute(
        select(DailyPrice.date).where(
            DailyPrice.asset_id == asset_id,
            DailyPrice.date.in_(dates),
        )
    )
    existing = {row[0] for row in result}
    for r in rows:
        if r.date not in existing:
            db.add(DailyPrice(asset_id=asset_id, date=r.date, close=r.close, volume=r.volume))


async def seed_fixture_data(db: AsyncSession) -> None:
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
        await _insert_new_prices(db, asset.id, rows)

    await db.commit()


async def ingest_asset(db: AsyncSession, asset: Asset, provider: object) -> int:
    rows: list[PriceRow] = await provider.fetch_ohlcv(asset.symbol, 90)  # type: ignore[attr-defined]
    await _insert_new_prices(db, asset.id, rows)
    asset.updated_at = datetime.now(UTC)
    await db.commit()
    return len(rows)
