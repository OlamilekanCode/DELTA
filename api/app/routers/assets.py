from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.intraday_price import IntradayPrice
from app.models.price import DailyPrice
from app.models.quote import AssetQuote
from app.schemas.asset import AssetHistoryOut, AssetHistoryPoint, AssetListOut, AssetOut
from app.services.access import free_only_clause, get_access_context, require_asset_access
from app.services.intraday import BUCKET_MINUTES, floor_to_bucket
from app.services.market_calendar import recent_session_dates, session_open_close

router = APIRouter()

# Intraday ranges apply completely different semantics per asset type:
# stocks trade in discrete ~6.5h sessions (5 days/week), crypto trades
# continuously. Stock ranges are session-count based via the XNYS calendar;
# crypto ranges are plain time cutoffs. "4H" for stocks is the tail of the
# most recent session rather than its own session count.
_INTRADAY_STOCK_SESSIONS: dict[str, int] = {"4H": 1, "1D": 1, "1W": 5, "1M": 20}
_INTRADAY_STOCK_TAIL_BUCKETS: dict[str, int | None] = {"4H": 8, "1D": None, "1W": None, "1M": None}
_INTRADAY_CRYPTO_HOURS: dict[str, float] = {"4H": 4, "1D": 24, "1W": 24 * 7, "1M": 24 * 30}

# Range -> days of daily history to return.
_DAILY_RANGE_DAYS: dict[str, int] = {
    "3M": 90,
    "1Y": 365,
}
_INTRADAY_RANGE_KEYS = frozenset(_INTRADAY_STOCK_SESSIONS)


async def _latest_prices(db: AsyncSession) -> dict[int, DailyPrice]:
    """Most recent DailyPrice row per asset_id."""
    sub = (
        select(DailyPrice.asset_id, func.max(DailyPrice.date).label("max_date"))
        .group_by(DailyPrice.asset_id)
        .subquery()
    )
    result = await db.execute(
        select(DailyPrice).join(
            sub,
            (DailyPrice.asset_id == sub.c.asset_id) & (DailyPrice.date == sub.c.max_date),
        )
    )
    return {row.asset_id: row for row in result.scalars().all()}


async def _latest_quotes(db: AsyncSession) -> dict[int, AssetQuote]:
    """Latest AssetQuote row per asset_id (one row per crypto asset)."""
    result = await db.execute(select(AssetQuote))
    return {row.asset_id: row for row in result.scalars().all()}


def _asset_out(
    asset: Asset,
    price_row: DailyPrice | None,
    quote_row: AssetQuote | None = None,
) -> AssetOut:
    # Crypto: prefer AssetQuote for current price and quote metadata
    if asset.asset_type == "crypto" and quote_row is not None:
        return AssetOut(
            symbol=asset.symbol,
            name=asset.name,
            category=asset.category,
            asset_type=asset.asset_type,
            access=asset.access,
            coingecko_id=asset.coingecko_id,
            last_price=quote_row.price_usd,
            last_price_date=quote_row.ts.date().isoformat() if quote_row.ts else None,
            is_demo=quote_row.is_demo,
            change_24h_pct=quote_row.change_24h_pct,
            market_cap_usd=quote_row.market_cap_usd,
            volume_24h_usd=quote_row.volume_24h_usd,
            quote_ts=quote_row.ts.isoformat() if quote_row.ts else None,
            quote_provider=quote_row.provider,
        )
    # Stocks and crypto fallback: use DailyPrice
    return AssetOut(
        symbol=asset.symbol,
        name=asset.name,
        category=asset.category,
        asset_type=asset.asset_type,
        access=asset.access,
        coingecko_id=asset.coingecko_id,
        last_price=price_row.close if price_row else None,
        last_price_date=price_row.date if price_row else None,
        is_demo=price_row.is_demo if price_row else None,
    )


@router.get("/assets", response_model=AssetListOut)
async def list_assets(
    request: Request,
    type: Literal["crypto", "stock"] | None = None,
    db: AsyncSession = Depends(get_db),
) -> AssetListOut:
    ctx = await get_access_context(request, db)
    stmt = select(Asset).order_by(Asset.symbol)
    if type:
        stmt = stmt.where(Asset.asset_type == type)
    clause = free_only_clause(ctx)
    if clause is not None:
        stmt = stmt.where(clause)
    result = await db.execute(stmt)
    assets = result.scalars().all()
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return AssetListOut(assets=[_asset_out(a, price_map.get(a.id), quote_map.get(a.id)) for a in assets])


@router.get("/assets/search", response_model=AssetListOut)
async def search_assets(
    request: Request,
    q: str = Query(default="", max_length=100),
    type: Literal["crypto", "stock"] | None = None,
    db: AsyncSession = Depends(get_db),
) -> AssetListOut:
    ctx = await get_access_context(request, db)
    stmt = select(Asset).order_by(Asset.symbol)
    if type:
        stmt = stmt.where(Asset.asset_type == type)
    clause = free_only_clause(ctx)
    if clause is not None:
        stmt = stmt.where(clause)
    if q.strip():
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Asset.symbol).like(pattern),
                func.lower(Asset.name).like(pattern),
                func.lower(Asset.category).like(pattern),
            )
        )
    result = await db.execute(stmt)
    assets = result.scalars().all()
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return AssetListOut(assets=[_asset_out(a, price_map.get(a.id), quote_map.get(a.id)) for a in assets])


@router.get("/assets/{symbol}", response_model=AssetOut)
async def get_asset(symbol: str, request: Request, db: AsyncSession = Depends(get_db)) -> AssetOut:
    result = await db.execute(
        select(Asset).where(func.upper(Asset.symbol) == symbol.upper())
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol!r} not found")
    await require_asset_access(request, db, asset)
    price_map = await _latest_prices(db)
    quote_map = await _latest_quotes(db)
    return _asset_out(asset, price_map.get(asset.id), quote_map.get(asset.id))


@router.get("/assets/{symbol}/history", response_model=AssetHistoryOut)
async def get_asset_history(
    symbol: str,
    request: Request,
    days: int = Query(default=90, ge=7, le=365),
    range: Literal["4H", "1D", "1W", "1M", "3M", "1Y"] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> AssetHistoryOut:
    result = await db.execute(
        select(Asset).where(func.upper(Asset.symbol) == symbol.upper())
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {symbol!r} not found")
    await require_asset_access(request, db, asset)

    if range in _INTRADAY_RANGE_KEYS:
        return await _asset_history_intraday(db, asset, range)
    return await _asset_history_daily(db, asset, range, _DAILY_RANGE_DAYS.get(range, days))


def _expected_daily_count(asset: Asset, days: int) -> int:
    """Theoretical max daily points in the window: NYSE sessions actually
    falling within the last `days` calendar days for stocks, calendar days
    for crypto (which trades every day)."""
    if asset.asset_type == "stock":
        from datetime import date

        cutoff_date = date.today() - timedelta(days=days)
        # recent_session_dates(count=N) returns the most recent N session
        # dates, which — since not every calendar day is a session — span
        # MORE than N calendar days. Over-fetch, then filter to the actual
        # calendar window so the expected count matches the query's cutoff.
        sessions = recent_session_dates(count=days)
        return len([s for s in sessions if s >= cutoff_date])
    return days


async def _asset_history_daily(
    db: AsyncSession, asset: Asset, range_key: str | None, days: int
) -> AssetHistoryOut:
    from datetime import date

    range_start_date = date.today() - timedelta(days=days)
    cutoff = range_start_date.isoformat()
    prices_result = await db.execute(
        select(DailyPrice)
        .where(DailyPrice.asset_id == asset.id, DailyPrice.date >= cutoff)
        .order_by(DailyPrice.date.asc())
    )
    prices = prices_result.scalars().all()

    is_demo: bool | None = None
    if prices:
        is_demo = any(p.is_demo for p in prices)

    provider = "fixture" if is_demo else ("coingecko" if asset.asset_type == "crypto" else "marketstack")

    expected = _expected_daily_count(asset, days)
    point_count = len(prices)
    completeness = min(1.0, point_count / expected) if expected else None

    return AssetHistoryOut(
        symbol=asset.symbol,
        asset_type=asset.asset_type,
        prices=[AssetHistoryPoint(date=p.date, close=p.close) for p in prices],
        is_demo=is_demo,
        provider=provider,
        requested_range=range_key,
        range_start=cutoff,
        range_end=date.today().isoformat(),
        point_count=point_count,
        expected_point_count=expected,
        completeness=completeness,
    )


def _intraday_window_start(asset: Asset, range_key: str, now: datetime) -> datetime:
    """The UTC start of the query window for an intraday range, branched by
    asset type: stocks use XNYS session boundaries, crypto uses a plain
    time cutoff (crypto trades continuously, so session semantics don't apply).
    """
    if asset.asset_type == "stock":
        session_count = _INTRADAY_STOCK_SESSIONS[range_key]
        sessions = recent_session_dates(now, count=session_count)
        earliest_open, _ = session_open_close(sessions[0])
        return earliest_open
    hours = _INTRADAY_CRYPTO_HOURS[range_key]
    return now - timedelta(hours=hours)


def _session_bucket_count(session_date) -> int:
    """Actual number of 30-minute buckets in a trading session. A regular
    session has 13, but NYSE early closes (day before Thanksgiving, July
    3rd, Christmas Eve, etc.) run shorter — assuming a flat 13 for those
    days would make a fully-populated shortened session look permanently
    incomplete."""
    session_open, session_close = session_open_close(session_date)
    return int((session_close - session_open).total_seconds() // (BUCKET_MINUTES * 60))


def _expected_intraday_count(asset: Asset, range_key: str, window_start: datetime, now: datetime) -> int:
    if asset.asset_type == "stock":
        session_count = _INTRADAY_STOCK_SESSIONS[range_key]
        sessions = recent_session_dates(now, count=session_count)
        total = sum(_session_bucket_count(s) for s in sessions)
        tail = _INTRADAY_STOCK_TAIL_BUCKETS[range_key]
        return min(tail, total) if tail is not None else total
    # Crypto rolls continuously, so "now" always sits inside a still-open
    # bucket that never appears in the DB (candles are only ever written
    # once complete). Counting hours*2 as "expected" would therefore
    # permanently read one bucket short (e.g. 47/48) even with a fully
    # populated window — expected must be the count of buckets that have
    # actually had a chance to close by "now".
    latest_completed_bucket_start = floor_to_bucket(now) - timedelta(minutes=BUCKET_MINUTES)
    if latest_completed_bucket_start < window_start:
        return 0
    span_minutes = (latest_completed_bucket_start - window_start).total_seconds() / 60
    return int(span_minutes // BUCKET_MINUTES) + 1


async def _asset_history_intraday(db: AsyncSession, asset: Asset, range_key: str) -> AssetHistoryOut:
    now = datetime.now(UTC)
    window_start = _intraday_window_start(asset, range_key, now)

    base_filters = (
        IntradayPrice.asset_id == asset.id,
        IntradayPrice.interval == "30m",
        IntradayPrice.bucket_ts >= window_start,
    )
    # "4H" for stocks is a tail slice of the current session, not its own
    # session window — fetch the session descending-limited then re-sort.
    tail = _INTRADAY_STOCK_TAIL_BUCKETS.get(range_key) if asset.asset_type == "stock" else None
    if tail is not None:
        result = await db.execute(
            select(IntradayPrice).where(*base_filters).order_by(IntradayPrice.bucket_ts.desc()).limit(tail)
        )
        rows = list(reversed(result.scalars().all()))
    else:
        result = await db.execute(
            select(IntradayPrice).where(*base_filters).order_by(IntradayPrice.bucket_ts.asc())
        )
        rows = list(result.scalars().all())

    is_demo: bool | None = None
    if rows:
        is_demo = any(r.is_demo for r in rows)

    provider = "fixture" if is_demo else ("coingecko" if asset.asset_type == "crypto" else "marketstack")

    expected = _expected_intraday_count(asset, range_key, window_start, now)
    point_count = len(rows)
    completeness = min(1.0, point_count / expected) if expected else None

    return AssetHistoryOut(
        symbol=asset.symbol,
        asset_type=asset.asset_type,
        prices=[
            AssetHistoryPoint(date=r.bucket_ts.date().isoformat(), close=r.close, ts=r.bucket_ts.isoformat())
            for r in rows
        ],
        is_demo=is_demo,
        provider=provider,
        collecting_data=point_count < expected,
        requested_range=range_key,
        range_start=window_start.isoformat(),
        range_end=now.isoformat(),
        point_count=point_count,
        expected_point_count=expected,
        completeness=completeness,
    )
