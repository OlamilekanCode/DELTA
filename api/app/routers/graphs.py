import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.intraday_exposure_score import IntradayExposureScore
from app.models.intraday_price import IntradayPrice
from app.schemas.correlation import StockInfo
from app.schemas.graphs import GraphEdge, GraphNode, GraphResult
from app.services.access import AccessContext, free_only_clause, require_asset_access
from app.services.freshness import intraday_status
from app.services.intraday import BUCKET_MINUTES, MIN_INTRADAY_OBS, stock_candle_count
from app.services.market_calendar import get_market_status, upcoming_session_dates

router = APIRouter()

_GRAPH_MAX_NODES = 12
_BUCKETS_PER_SESSION = int((6.5 * 60) // BUCKET_MINUTES)  # regular NYSE session length


@router.get("/graphs/{stock_symbol}", response_model=GraphResult)
async def get_graph(
    stock_symbol: str,
    request: Request,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    interval: str = Query(default="historical", pattern="^(historical|live)$"),
    db: AsyncSession = Depends(get_db),
) -> GraphResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")
    ctx = await require_asset_access(request, db, stock)

    if interval == "live":
        return await _get_live_graph(db, stock, ctx, min_score)
    return await _get_historical_graph(db, stock, ctx, min_score)


async def _get_historical_graph(db: AsyncSession, stock: Asset, ctx: AccessContext, min_score: float) -> GraphResult:
    # Filter on abs(score) so inverse relationships are not silently excluded.
    # Join against Asset here (not filter-after-load) so a guest's LIMIT is
    # applied over only the crypto they're allowed to see.
    stored_stmt = (
        select(StoredExposureScore)
        .join(Asset, Asset.id == StoredExposureScore.crypto_id)
        .where(
            StoredExposureScore.stock_id == stock.id,
            func.abs(StoredExposureScore.score) >= min_score,
        )
    )
    clause = free_only_clause(ctx)
    if clause is not None:
        stored_stmt = stored_stmt.where(clause)
    stored_stmt = stored_stmt.order_by(func.abs(StoredExposureScore.score).desc()).limit(_GRAPH_MAX_NODES)
    stored_result = await db.execute(stored_stmt)
    stored = stored_result.scalars().all()

    crypto_ids = [s.crypto_id for s in stored]
    crypto_result = await db.execute(select(Asset).where(Asset.id.in_(crypto_ids)))
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    computed_at = stored[0].computed_at if stored else None
    is_demo = any(s.is_demo for s in stored) if stored else True

    nodes, edges = _build_nodes_and_edges(stock, [(s.crypto_id, s.score) for s in stored], crypto_by_id)

    return GraphResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        nodes=nodes,
        edges=edges,
        demo=is_demo,
        computed_at=computed_at,
        interval="historical",
    )


async def _get_live_graph(db: AsyncSession, stock: Asset, ctx: AccessContext, min_score: float) -> GraphResult:
    stored_stmt = (
        select(IntradayExposureScore)
        .join(Asset, Asset.id == IntradayExposureScore.crypto_id)
        .where(IntradayExposureScore.stock_id == stock.id)
    )
    clause = free_only_clause(ctx)
    if clause is not None:
        stored_stmt = stored_stmt.where(clause)
    stored_result = await db.execute(stored_stmt)
    stored_all = stored_result.scalars().all()

    market_status = get_market_status()
    ready_rows = [s for s in stored_all if s.data_quality == "ok" and abs(s.score) >= min_score]

    if not ready_rows:
        if stored_all:
            current_count = max(s.observations for s in stored_all)
            is_demo = any(s.is_demo for s in stored_all)
        else:
            current_count, is_demo = await _never_scored_progress(db, stock)

        remaining = max(MIN_INTRADAY_OBS - current_count, 0)
        sessions_needed = max(1, math.ceil(remaining / _BUCKETS_PER_SESSION))
        upcoming = upcoming_session_dates(count=sessions_needed)
        estimated_ready = upcoming[-1].isoformat() if upcoming else None
        return GraphResult(
            stock=StockInfo(symbol=stock.symbol, name=stock.name),
            nodes=[GraphNode(id=stock.symbol, symbol=stock.symbol, name=stock.name,
                              category=stock.category, score=None, is_center=True)],
            edges=[],
            demo=is_demo,
            computed_at=None,
            interval="live",
            status="collecting_data",
            current_count=current_count,
            required_count=MIN_INTRADAY_OBS,
            estimated_ready=estimated_ready,
            freshness="collecting_data",
            market_is_open=market_status.is_open,
        )

    ready_rows.sort(key=lambda s: abs(s.score), reverse=True)
    ready_rows = ready_rows[:_GRAPH_MAX_NODES]

    crypto_ids = [s.crypto_id for s in ready_rows]
    crypto_result = await db.execute(select(Asset).where(Asset.id.in_(crypto_ids)))
    crypto_by_id = {a.id: a for a in crypto_result.scalars().all()}

    is_demo = any(s.is_demo for s in ready_rows)
    data_ts = min((s.data_ts for s in ready_rows), default=None)
    freshness = intraday_status(data_ts)

    nodes, edges = _build_nodes_and_edges(stock, [(s.crypto_id, s.score) for s in ready_rows], crypto_by_id)

    return GraphResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        nodes=nodes,
        edges=edges,
        demo=is_demo,
        computed_at=data_ts,
        interval="live",
        status="ready",
        freshness=freshness,
        market_is_open=market_status.is_open,
    )


async def _never_scored_progress(db: AsyncSession, stock: Asset) -> tuple[int, bool]:
    """Mirrors the fallback progress signal in routers/intraday.py for a
    stock with no stored IntradayExposureScore rows at all yet."""
    candle_count = await stock_candle_count(db, stock.id)
    demo_result = await db.execute(
        select(IntradayPrice.is_demo)
        .where(IntradayPrice.asset_id == stock.id, IntradayPrice.interval == "30m")
        .order_by(IntradayPrice.bucket_ts.desc())
        .limit(1)
    )
    is_demo = demo_result.scalar_one_or_none()
    return candle_count, True if is_demo is None else is_demo


def _build_nodes_and_edges(
    stock: Asset, scored: list[tuple[int, float]], crypto_by_id: dict[int, Asset]
) -> tuple[list[GraphNode], list[GraphEdge]]:
    center_node = GraphNode(
        id=stock.symbol, symbol=stock.symbol, name=stock.name,
        category=stock.category, score=None, is_center=True,
    )
    nodes: list[GraphNode] = [center_node]
    edges: list[GraphEdge] = []
    for crypto_id, score in scored:
        ca = crypto_by_id.get(crypto_id)
        if not ca:
            continue
        nodes.append(GraphNode(
            id=ca.symbol, symbol=ca.symbol, name=ca.name,
            category=ca.category, score=score, is_center=False,
        ))
        edges.append(GraphEdge(
            source=stock.symbol, target=ca.symbol,
            weight=round(abs(score), 4), score=score,
            direction="positive" if score >= 0 else "inverse",
        ))
    return nodes, edges
