from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.schemas.correlation import StockInfo
from app.schemas.graphs import GraphEdge, GraphNode, GraphResult
from app.services.scoring import recompute_all_scores

router = APIRouter()

_GRAPH_MAX_NODES = 12


@router.get("/graphs/{stock_symbol}", response_model=GraphResult)
async def get_graph(
    stock_symbol: str,
    min_score: float = 0.0,
    db: AsyncSession = Depends(get_db),
) -> GraphResult:
    symbol = stock_symbol.upper()

    stock_result = await db.execute(
        select(Asset).where(Asset.symbol == symbol, Asset.asset_type == "stock")
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {symbol!r} not found")

    stored_result = await db.execute(
        select(StoredExposureScore)
        .where(StoredExposureScore.stock_id == stock.id, StoredExposureScore.score >= min_score)
        .order_by(StoredExposureScore.score.desc())
        .limit(_GRAPH_MAX_NODES)
    )
    stored = stored_result.scalars().all()

    if not stored:
        await recompute_all_scores(db)
        stored_result2 = await db.execute(
            select(StoredExposureScore)
            .where(StoredExposureScore.stock_id == stock.id, StoredExposureScore.score >= min_score)
            .order_by(StoredExposureScore.score.desc())
            .limit(_GRAPH_MAX_NODES)
        )
        stored = stored_result2.scalars().all()

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
        edges.append(GraphEdge(source=stock.symbol, target=ca.symbol, weight=s.score))

    return GraphResult(
        stock=StockInfo(symbol=stock.symbol, name=stock.name),
        nodes=nodes,
        edges=edges,
        demo=is_demo,
        computed_at=computed_at,
    )
