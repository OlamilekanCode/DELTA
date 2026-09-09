from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.price import DailyPrice
from app.services.correlation import MIN_OBSERVATIONS, PricePoint, compute_exposure_scores


async def _load_prices(
    db: AsyncSession, asset_id: int, days: int, prefer_adj_close: bool
) -> tuple[list[PricePoint], bool]:
    """Load daily prices, preferring adj_close over close when available (stocks only).

    Rejects missing, zero or negative prices. Returns the aligned points plus
    whether any row had to fall back from adj_close to close.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    result = await db.execute(
        select(DailyPrice.date, DailyPrice.close, DailyPrice.adj_close)
        .where(DailyPrice.asset_id == asset_id, DailyPrice.date >= cutoff)
        .order_by(DailyPrice.date.asc())
    )
    points: list[PricePoint] = []
    any_fallback = False
    for r in result.all():
        used_fallback = False
        if prefer_adj_close and r.adj_close is not None and r.adj_close > 0:
            effective = r.adj_close
        else:
            effective = r.close
            used_fallback = prefer_adj_close
        if effective is None or effective <= 0:
            continue
        if used_fallback:
            any_fallback = True
        points.append(PricePoint(date=r.date, close=effective))
    return points, any_fallback


async def recompute_all_scores(db: AsyncSession) -> int:
    """Precompute Pearson Exposure Scores for every stock × crypto pair.

    The complete replacement set is computed in memory first (no writes);
    only once it is ready does this upsert existing rows / insert new ones /
    remove pairs no longer present in the fresh set. A provider or
    calculation failure before that point leaves the previously committed
    scores completely untouched — never a delete-then-partial-insert.
    """
    stocks_result = await db.execute(
        select(Asset).where(Asset.asset_type == "stock").order_by(Asset.symbol)
    )
    stocks = stocks_result.scalars().all()

    crypto_result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto").order_by(Asset.symbol)
    )
    crypto_assets = crypto_result.scalars().all()

    crypto_id_map: dict[str, int] = {a.symbol: a.id for a in crypto_assets}
    crypto_asset_map: dict[str, Asset] = {a.symbol: a for a in crypto_assets}
    now = datetime.now(UTC)

    # Preload is_demo status for ALL relevant assets in one query.
    # An asset is considered demo if ANY of its stored price rows has is_demo=True.
    all_asset_ids = [s.id for s in stocks] + [c.id for c in crypto_assets]
    if all_asset_ids:
        demo_rows = await db.execute(
            select(DailyPrice.asset_id)
            .where(
                DailyPrice.asset_id.in_(all_asset_ids),
                DailyPrice.is_demo == True,  # noqa: E712
            )
            .distinct()
        )
        demo_asset_ids: set[int] = {row.asset_id for row in demo_rows.all()}
    else:
        demo_asset_ids = set()

    # Crypto prices don't vary per stock — load them once and reuse across every
    # stock's computation instead of re-querying inside the stock loop.
    crypto_map: dict[str, tuple[str, str, list[PricePoint]]] = {}
    for ca in crypto_assets:
        cp, _ = await _load_prices(db, ca.id, 90, prefer_adj_close=False)
        if len(cp) >= 2:
            crypto_map[ca.symbol] = (ca.name, ca.category, cp)

    # ── Pure computation: build the complete replacement set, no writes yet. ──
    new_rows: list[dict] = []
    for stock in stocks:
        stock_prices, stock_adj_close_fallback = await _load_prices(
            db, stock.id, 90, prefer_adj_close=True
        )
        if len(stock_prices) < 2:
            continue

        stock_is_demo = stock.id in demo_asset_ids
        scores = compute_exposure_scores(stock_prices, crypto_map)

        for s in scores:
            crypto_id = crypto_id_map.get(s.symbol)
            ca = crypto_asset_map.get(s.symbol)
            if crypto_id is None or ca is None:
                continue
            # Pair-level is_demo: True if EITHER the stock OR the crypto has demo prices.
            # Only mark live (False) when both assets use real provider data.
            pair_is_demo = stock_is_demo or (ca.id in demo_asset_ids)

            # Flags are additive, never mutually exclusive — crypto_daily_proxy
            # is honest and true for every score today (crypto prices are daily
            # UTC closes, not selected against the actual XNYS session close —
            # see docs/methodology.md) and must never be dropped just because
            # adj_close_missing or low_observations also applies.
            flags = ["crypto_daily_proxy"]
            if stock_adj_close_fallback:
                flags.append("adj_close_missing")
            if s.observations < MIN_OBSERVATIONS * 1.2:
                flags.append("low_observations")

            new_rows.append({
                "stock_id": stock.id,
                "crypto_id": crypto_id,
                "score": s.score,
                "raw_correlation": s.raw_correlation,
                "observations": s.observations,
                "computed_at": now,
                "model_version": "v1",
                "is_demo": pair_is_demo,
                "data_quality": ",".join(flags),
                "data_ts": datetime.fromisoformat(s.last_date).replace(tzinfo=UTC),
            })

    # ── Upsert the complete set, then remove only pairs no longer present. ──
    existing_result = await db.execute(select(StoredExposureScore))
    existing_by_pair = {(row.stock_id, row.crypto_id): row for row in existing_result.scalars().all()}

    seen_pairs: set[tuple[int, int]] = set()
    for nr in new_rows:
        key = (nr["stock_id"], nr["crypto_id"])
        seen_pairs.add(key)
        row = existing_by_pair.get(key)
        if row is not None:
            for field, value in nr.items():
                setattr(row, field, value)
        else:
            db.add(StoredExposureScore(**nr))

    obsolete_ids = [row.id for key, row in existing_by_pair.items() if key not in seen_pairs]
    if obsolete_ids:
        await db.execute(delete(StoredExposureScore).where(StoredExposureScore.id.in_(obsolete_ids)))

    await db.commit()
    return len(new_rows)
