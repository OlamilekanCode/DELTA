from pydantic import BaseModel


class AssetOut(BaseModel):
    symbol: str
    name: str
    category: str
    asset_type: str
    access: str = "free"  # "free" | "holder"
    coingecko_id: str | None = None
    last_price: float | None = None
    last_price_date: str | None = None
    is_demo: bool | None = None
    # Quote fields — populated for crypto assets only
    change_24h_pct: float | None = None
    market_cap_usd: float | None = None
    volume_24h_usd: float | None = None
    quote_ts: str | None = None
    quote_provider: str | None = None

    model_config = {"from_attributes": True}


class AssetListOut(BaseModel):
    assets: list[AssetOut]


class AssetHistoryPoint(BaseModel):
    date: str
    close: float
    ts: str | None = None  # full ISO8601 timestamp, populated for intraday ranges only


class AssetHistoryOut(BaseModel):
    symbol: str
    asset_type: str
    prices: list[AssetHistoryPoint]
    is_demo: bool | None
    provider: str
    collecting_data: bool | None = None
    requested_range: str | None = None
    range_start: str | None = None  # ISO8601, start of the requested window
    range_end: str | None = None  # ISO8601, end of the requested window
    point_count: int = 0
    expected_point_count: int | None = None  # theoretical max for the window; None if unknown
    completeness: float | None = None  # point_count / expected_point_count, clamped to [0, 1]
