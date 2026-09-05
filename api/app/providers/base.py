from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class PriceRow:
    date: str    # "YYYY-MM-DD"
    close: float
    volume: float | None = None


@runtime_checkable
class ProviderProtocol(Protocol):
    async def fetch_ohlcv(self, symbol: str, days: int) -> list[PriceRow]: ...


class ProviderError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)
