from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class PriceRow:
    date: str    # "YYYY-MM-DD"
    close: float
    volume: float | None = None


@dataclass
class QuoteRow:
    symbol: str
    price_usd: float
    market_cap_usd: float | None
    volume_24h_usd: float | None
    change_24h_pct: float | None
    ts: datetime


@runtime_checkable
class ProviderProtocol(Protocol):
    async def fetch_ohlcv(self, symbol: str, days: int) -> list[PriceRow]: ...


class ProviderError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
