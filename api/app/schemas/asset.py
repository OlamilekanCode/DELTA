from pydantic import BaseModel


class AssetOut(BaseModel):
    symbol: str
    name: str
    category: str
    asset_type: str
    coingecko_id: str | None = None
    last_price: float | None = None
    last_price_date: str | None = None
    is_demo: bool | None = None

    model_config = {"from_attributes": True}


class AssetListOut(BaseModel):
    assets: list[AssetOut]


class AssetHistoryPoint(BaseModel):
    date: str
    close: float


class AssetHistoryOut(BaseModel):
    symbol: str
    asset_type: str
    prices: list[AssetHistoryPoint]
    is_demo: bool | None
    provider: str
