from datetime import datetime

from pydantic import BaseModel

from app.schemas.correlation import ExposureScoreOut, StockInfo


class ExposuresResult(BaseModel):
    stock: StockInfo
    scores: list[ExposureScoreOut]
    computed_at: datetime | None
    stale: bool
    demo: bool
    model_version: str = "v1"
    window_days: int = 90
