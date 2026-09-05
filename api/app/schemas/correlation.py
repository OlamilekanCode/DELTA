from datetime import datetime

from pydantic import BaseModel


class ExposureScoreOut(BaseModel):
    symbol: str
    name: str
    category: str
    score: float
    raw_correlation: float
    observations: int


class PriceSeriesPoint(BaseModel):
    date: str
    value: float


class PriceSeriesOut(BaseModel):
    stock: list[PriceSeriesPoint]
    crypto: dict[str, list[PriceSeriesPoint]]


class StockInfo(BaseModel):
    symbol: str
    name: str


class CorrelationResult(BaseModel):
    stock: StockInfo
    scores: list[ExposureScoreOut]
    price_series: PriceSeriesOut
    demo: bool
    generated_at: datetime
