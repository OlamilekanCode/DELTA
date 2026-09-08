from datetime import datetime

from pydantic import BaseModel

from app.schemas.correlation import StockInfo


class GraphNode(BaseModel):
    id: str
    symbol: str
    name: str
    category: str
    score: float | None
    is_center: bool


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float        # abs(score) — use for edge thickness
    score: float         # signed Pearson r
    direction: str       # "positive" | "inverse"


class GraphResult(BaseModel):
    stock: StockInfo
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    demo: bool
    computed_at: datetime | None
