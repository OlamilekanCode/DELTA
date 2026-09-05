from datetime import date, timedelta

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.providers.base import PriceRow, ProviderError


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ProviderError):
        return exc.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.TransportError)


class MarketstackProvider:
    BASE = "https://api.marketstack.com/v1"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_ohlcv(self, symbol: str, days: int) -> list[PriceRow]:
        date_to = date.today()
        date_from = date_to - timedelta(days=days + 5)  # buffer for weekends/holidays

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.BASE}/eod",
                params={
                    "access_key": self.api_key,
                    "symbols": symbol.upper(),
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "limit": days + 10,
                    "sort": "ASC",
                },
            )

        if r.status_code == 429:
            raise ProviderError(429, "Marketstack rate limited")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"Marketstack error {r.status_code}")

        data = r.json().get("data", [])
        rows: list[PriceRow] = []
        for item in data:
            raw_date: str = item.get("date", "")
            close: float = float(item.get("close", 0))
            if not raw_date or close <= 0:
                continue
            rows.append(PriceRow(date=raw_date[:10], close=close))

        return rows[-days:]
