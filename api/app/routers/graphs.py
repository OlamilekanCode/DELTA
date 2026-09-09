from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.schemas.correlation import StockInfo
from app.schemas.graphs import GraphEdge, GraphNode, GraphResult
from app.services.access import free_only_clause, require_asset_access

router = APIRouter()

_GRAPH_MAX_NODES = 12


@router.get("/graphs/{stock_symbol}", response_model=GraphResult)
async def get_graph(
    stock_symbol: str,
    request: Request,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
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

    center_node = GraphNode(
        id=stock.symbol,
        symbol=stock.symbol,
        name=stock.name,
        category=stock.category,
        score=None,
        is_center=True,
    )
    nodes: list[GraphNode] = [center_node]
    edges: list[GraphEdge] = []

    for s in stored:
        ca = crypto_by_id.get(s.crypto_id)
        if not ca:
            continue
        nodes.append(GraphNode(
            id=ca.symbol,
            symbol=ca.symbol,
            name=ca.name,
            category=ca.category,
            score=s.score,
            is_center=False,
        ))
        edges.append(GraphEdge(
            source=stock.symbol,
            target=ca.symbol,
            weight=round(abs(s.score), 4),
            score=s.score,
            direction="positive" if s.score >= 0 else "inverse",
        ))

    return GraphResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        nodes=nodes,
        edges=edges,
        demo=is_demo,
        computed_at=computed_at,
    )
