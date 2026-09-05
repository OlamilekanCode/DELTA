import asyncio
from datetime import datetime, timezone

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.providers.base import PriceRow, ProviderError


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ProviderError):
        return exc.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, httpx.TransportError)


class CoinGeckoProvider:
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_ohlcv(self, coingecko_id: str, days: int) -> list[PriceRow]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-cg-pro-api-key"] = self.api_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self.BASE}/coins/{coingecko_id}/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                headers=headers,
            )

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "60"))
            await asyncio.sleep(min(retry_after, 60))
            raise ProviderError(429, f"CoinGecko rate limited — retry after {retry_after}s")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"CoinGecko error {r.status_code}")

        data: dict = r.json()
        return [
            PriceRow(
                date=datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                close=round(price, 6),
            )
            for ts, price in data.get("prices", [])
        ]
