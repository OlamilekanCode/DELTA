from pydantic import BaseModel


class AssetOut(BaseModel):
    symbol: str
    name: str
    category: str
    asset_type: str
    coingecko_id: str | None = None

    model_config = {"from_attributes": True}


class AssetListOut(BaseModel):
    assets: list[AssetOut]
