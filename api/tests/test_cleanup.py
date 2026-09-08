from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.commands import cmd_cleanup_old_data
from app.models.asset import Asset
from app.models.intraday_price import IntradayPrice


@pytest.mark.asyncio
async def test_cleanup_deletes_only_stale_intraday_rows(db: AsyncSession) -> None:
    asset_result = await db.execute(select(Asset).where(Asset.symbol == "NVDA"))
    asset = asset_result.scalar_one()
    now = datetime.now(UTC)

    stale = IntradayPrice(
        asset_id=asset.id, bucket_ts=now - timedelta(days=100), interval="30m",
        open=1, high=1, low=1, close=1, provider="test", sample_count=1,
        data_quality="ok", is_demo=True, created_at=now, updated_at=now,
    )
    fresh = IntradayPrice(
        asset_id=asset.id, bucket_ts=now - timedelta(days=1), interval="30m",
        open=1, high=1, low=1, close=1, provider="test", sample_count=1,
        data_quality="ok", is_demo=True, created_at=now, updated_at=now,
    )
    db.add_all([stale, fresh])
    await db.commit()

    await cmd_cleanup_old_data()

    remaining = await db.execute(
        select(IntradayPrice).where(IntradayPrice.asset_id == asset.id, IntradayPrice.provider == "test")
    )
    rows = remaining.scalars().all()
    assert len(rows) == 1
    assert rows[0].bucket_ts.replace(tzinfo=UTC) == fresh.bucket_ts
