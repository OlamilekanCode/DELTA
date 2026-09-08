from pydantic import BaseModel

from app.schemas.correlation import StockInfo


class IntradayScoreOut(BaseModel):
    symbol: str
    name: str
    category: str
    score: float
    observations: int


class IntradayResult(BaseModel):
    stock: StockInfo
    status: str  # "ready" | "collecting_data"
    scores: list[IntradayScoreOut]
    interval: str
    sessions_used: int
    demo: bool
    current_count: int | None = None
    required_count: int | None = None
    estimated_ready: str | None = None
