import asyncio
import logging
from datetime import datetime, timezone

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.providers.base import PriceRow, ProviderError, QuoteRow

log = logging.getLogger(__name__)

_MAX_BATCH = 250  # CoinGecko per_page limit


class CoinGeckoProvider:
    DEMO_BASE = "https://api.coingecko.com/api/v3"
    PRO_BASE = "https://pro-api.coingecko.com/api/v3"

    def __init__(self, api_key: str = "", api_type: str = "demo") -> None:
        self.api_key = api_key
        self.api_type = api_type  # "demo" | "pro"
        self.base = self.PRO_BASE if api_type == "pro" else self.DEMO_BASE

    @property
    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        header_name = "x-cg-pro-api-key" if self.api_type == "pro" else "x-cg-demo-api-key"
        return {header_name: self.api_key}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_ohlcv(self, coingecko_id: str, days: int) -> list[PriceRow]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self.base}/coins/{coingecko_id}/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                headers=self._headers,
            )

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "60"))
            log.warning("CoinGecko rate limited — sleeping %ss", min(retry_after, 60))
            await asyncio.sleep(min(retry_after, 60))
            raise ProviderError(429, f"CoinGecko rate limited — retry after {retry_after}s")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"CoinGecko error {r.status_code}: {r.text[:200]}")

        data: dict = r.json()
        seen: set[str] = set()
        rows: list[PriceRow] = []
        for ts, price in data.get("prices", []):
            date_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            if date_str not in seen:
                seen.add(date_str)
                rows.append(PriceRow(date=date_str, close=round(price, 8)))
        return rows

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_quotes_batch(self, coingecko_ids: list[str]) -> list[QuoteRow]:
        """Fetch current prices for up to 250 coins in one request."""
        ids_str = ",".join(coingecko_ids[:_MAX_BATCH])
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self.base}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": ids_str,
                    "order": "market_cap_desc",
                    "per_page": _MAX_BATCH,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "24h",
                },
                headers=self._headers,
            )

        if r.status_code == 429:
            raise ProviderError(429, "CoinGecko rate limited on batch quote")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"CoinGecko batch error {r.status_code}")

        now = datetime.now(timezone.utc)
        rows: list[QuoteRow] = []
        for item in r.json():
            rows.append(QuoteRow(
                symbol=item.get("symbol", "").upper(),
                price_usd=float(item.get("current_price") or 0),
                market_cap_usd=item.get("market_cap"),
                volume_24h_usd=item.get("total_volume"),
                change_24h_pct=item.get("price_change_percentage_24h"),
                ts=now,
            ))
        return rows
