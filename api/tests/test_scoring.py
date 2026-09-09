"""Tests for per-pair is_demo logic in recompute_all_scores."""

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.price import DailyPrice
from app.services import scoring as scoring_module
from app.services.scoring import recompute_all_scores


@pytest.mark.asyncio
async def test_demo_demo_all_pairs_are_demo(db: AsyncSession) -> None:
    """Both assets use fixture data → every pair is_demo=True."""
    n = await recompute_all_scores(db)
    assert n > 0

    result = await db.execute(select(StoredExposureScore))
    scores = result.scalars().all()
    assert scores, "Expected scores to be computed"
    assert all(s.is_demo for s in scores), "All pairs must be demo when fixture data used"


@pytest.mark.asyncio
async def test_real_real_no_pairs_are_demo(db: AsyncSession) -> None:
    """Both assets use real data → every pair is_demo=False."""
    await db.execute(update(DailyPrice).values(is_demo=False))
    await db.commit()

    n = await recompute_all_scores(db)
    assert n > 0

    result = await db.execute(select(StoredExposureScore))
    scores = result.scalars().all()
    assert scores
    assert all(not s.is_demo for s in scores), "No pair should be demo when both use real data"


@pytest.mark.asyncio
async def test_stock_real_crypto_demo_pairs_are_demo(db: AsyncSession) -> None:
    """Stock has real data, crypto has demo → pair is_demo=True (crypto contaminates)."""
    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == "NVDA")
    )
    stock = stock_result.scalar_one()

    # Mark NVDA prices as real; leave all crypto as demo
    await db.execute(
        update(DailyPrice)
        .where(DailyPrice.asset_id == stock.id)
        .values(is_demo=False)
    )
    await db.commit()

    n = await recompute_all_scores(db)
    assert n > 0

    result = await db.execute(
        select(StoredExposureScore).where(StoredExposureScore.stock_id == stock.id)
    )
    scores = result.scalars().all()
    assert scores, "Expected scores for NVDA"
    assert all(s.is_demo for s in scores), (
        "Pairs must be demo when the crypto side uses fixture prices"
    )


@pytest.mark.asyncio
async def test_stock_demo_crypto_real_pairs_are_demo(db: AsyncSession) -> None:
    """Stock has demo data, crypto has real → pair is_demo=True (stock contaminates)."""
    crypto_result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto")
    )
    crypto_assets = crypto_result.scalars().all()
    crypto_ids = [a.id for a in crypto_assets]

    # Mark all crypto prices as real; leave all stocks as demo
    await db.execute(
        update(DailyPrice)
        .where(DailyPrice.asset_id.in_(crypto_ids))
        .values(is_demo=False)
    )
    await db.commit()

    n = await recompute_all_scores(db)
    assert n > 0

    result = await db.execute(select(StoredExposureScore))
    scores = result.scalars().all()
    assert all(s.is_demo for s in scores), (
        "Pairs must be demo when the stock side uses fixture prices"
    )


@pytest.mark.asyncio
async def test_mixed_stocks_independent_demo_flags(db: AsyncSession) -> None:
    """Two stocks, one real and one demo, produce independent pair-level flags."""
    stocks_result = await db.execute(select(Asset).where(Asset.asset_type == "stock"))
    stocks = stocks_result.scalars().all()
    assert len(stocks) >= 2, "Need at least two stocks for this test"

    real_stock = stocks[0]
    demo_stock = stocks[1]

    # Mark real_stock prices as real; everything else stays demo
    await db.execute(
        update(DailyPrice)
        .where(DailyPrice.asset_id == real_stock.id)
        .values(is_demo=False)
    )
    await db.commit()

    await recompute_all_scores(db)

    real_scores = (
        await db.execute(
            select(StoredExposureScore).where(
                StoredExposureScore.stock_id == real_stock.id
            )
        )
    ).scalars().all()

    demo_scores = (
        await db.execute(
            select(StoredExposureScore).where(
                StoredExposureScore.stock_id == demo_stock.id
            )
        )
    ).scalars().all()

    # real_stock pairs: stock real + crypto demo → still demo (crypto contaminates)
    assert all(s.is_demo for s in real_scores), (
        "Pairs for real-data stock are still demo because crypto uses fixture data"
    )
    # demo_stock pairs: both demo → demo
    assert all(s.is_demo for s in demo_scores), (
        "Pairs for demo stock must be demo"
    )


@pytest.mark.asyncio
async def test_data_quality_always_includes_crypto_daily_proxy(db: AsyncSession) -> None:
    """crypto_daily_proxy is honest for every score today and must never be
    dropped just because another flag also applies."""
    n = await recompute_all_scores(db)
    assert n > 0

    scores = (await db.execute(select(StoredExposureScore))).scalars().all()
    for s in scores:
        assert s.data_quality is not None
        assert "crypto_daily_proxy" in s.data_quality.split(",")


@pytest.mark.asyncio
async def test_recompute_all_scores_upserts_same_pair_across_reruns(db: AsyncSession) -> None:
    """A second recompute with unchanged data must update the same stored
    rows (upsert), not delete-then-reinsert with fresh identities."""
    await recompute_all_scores(db)
    first = {
        (s.stock_id, s.crypto_id): s.id
        for s in (await db.execute(select(StoredExposureScore))).scalars().all()
    }
    assert first

    await recompute_all_scores(db)
    second = {
        (s.stock_id, s.crypto_id): s.id
        for s in (await db.execute(select(StoredExposureScore))).scalars().all()
    }
    assert first == second


@pytest.mark.asyncio
async def test_recompute_all_scores_preserves_previous_set_on_failure(db: AsyncSession, monkeypatch) -> None:
    """A calculation/provider failure must never leave the previous valid
    score set partially deleted — the whole replacement set is computed in
    memory before anything is written."""
    await recompute_all_scores(db)
    before = {
        (s.stock_id, s.crypto_id): s.score
        for s in (await db.execute(select(StoredExposureScore))).scalars().all()
    }
    assert before

    def boom(*args, **kwargs):
        raise RuntimeError("simulated provider/calculation failure")

    monkeypatch.setattr(scoring_module, "compute_exposure_scores", boom)

    with pytest.raises(RuntimeError):
        await recompute_all_scores(db)

    after = {
        (s.stock_id, s.crypto_id): s.score
        for s in (await db.execute(select(StoredExposureScore))).scalars().all()
    }
    assert after == before
