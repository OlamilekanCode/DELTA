from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.price import DailyPrice
from app.services.correlation import PricePoint, compute_exposure_scores


async def _load_prices(db: AsyncSession, asset_id: int, days: int) -> list[PricePoint]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    result = await db.execute(
        select(DailyPrice.date, DailyPrice.close)
        .where(DailyPrice.asset_id == asset_id, DailyPrice.date >= cutoff)
        .order_by(DailyPrice.date.asc())
    )
    return [PricePoint(date=r.date, close=r.close) for r in result.all()]


async def recompute_all_scores(db: AsyncSession) -> int:
    """Precompute Pearson Exposure Scores for every stock × crypto pair and persist them."""
    stocks_result = await db.execute(
        select(Asset).where(Asset.asset_type == "stock").order_by(Asset.symbol)
    )
    stocks = stocks_result.scalars().all()

    crypto_result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto").order_by(Asset.symbol)
    )
    crypto_assets = crypto_result.scalars().all()

    crypto_id_map: dict[str, int] = {a.symbol: a.id for a in crypto_assets}
    now = datetime.now(UTC)
    total = 0

    for stock in stocks:
        stock_prices = await _load_prices(db, stock.id, 90)
        if len(stock_prices) < 2:
            continue

        crypto_map: dict[str, tuple[str, str, list[PricePoint]]] = {}
        for ca in crypto_assets:
            cp = await _load_prices(db, ca.id, 90)
            if len(cp) >= 2:
                crypto_map[ca.symbol] = (ca.name, ca.category, cp)

        scores = compute_exposure_scores(stock_prices, crypto_map)

        # Determine demo status from stock prices
        demo_result = await db.execute(
            select(DailyPrice.is_demo)
            .where(DailyPrice.asset_id == stock.id, DailyPrice.is_demo == True)  # noqa: E712
            .limit(1)
        )
        is_demo = demo_result.scalar() is True

        # Delete existing scores for this stock before reinserting
        await db.execute(
            delete(StoredExposureScore).where(StoredExposureScore.stock_id == stock.id)
        )

        for s in scores:
            crypto_id = crypto_id_map.get(s.symbol)
            if crypto_id is None:
                continue
            db.add(StoredExposureScore(
                stock_id=stock.id,
                crypto_id=crypto_id,
                score=s.score,
                raw_correlation=s.raw_correlation,
                observations=s.observations,
                computed_at=now,
                model_version="v1",
                is_demo=is_demo,
            ))
            total += 1

    await db.commit()
    return total
