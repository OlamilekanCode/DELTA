from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.providers.base import PriceRow, ProviderError
from app.services.provider_usage import log_provider_call

if TYPE_CHECKING:
    from app.services.intraday import IntradayCandle


def _valid_adj_close(raw: object) -> float | None:
    """Reject missing, zero or negative adjusted-close values."""
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


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
        log_provider_call("marketstack", "eod", symbols=1, days=days)
        date_to = date.today()
        date_from = date_to - timedelta(days=days + 5)  # buffer for weekends/holidays

        async with httpx.AsyncClient(timeout=15.0) as client:
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
            raw_close = item.get("close")
            if not raw_date or raw_close is None:
                continue
            close: float = float(raw_close)
            if close <= 0:
                continue
            adj_close = _valid_adj_close(item.get("adj_close"))
            rows.append(PriceRow(date=raw_date[:10], close=close, adj_close=adj_close))

        return rows[-days:]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_eod_batch(self, symbols: list[str], days: int) -> dict[str, list[PriceRow]]:
        """Fetch EOD prices for multiple symbols in one API call.

        Note: Marketstack free plan counts each symbol in the batch as a separate request.
        Callers should be aware this may consume one request per symbol on the free tier.
        """
        log_provider_call("marketstack", "eod_batch", symbols=len(symbols), days=days)
        date_to = date.today()
        date_from = date_to - timedelta(days=days + 5)
        symbols_str = ",".join(s.upper() for s in symbols)

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f"{self.BASE}/eod",
                params={
                    "access_key": self.api_key,
                    "symbols": symbols_str,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "limit": (days + 10) * len(symbols),
                    "sort": "ASC",
                },
            )

        if r.status_code == 429:
            raise ProviderError(429, "Marketstack rate limited on batch")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"Marketstack batch error {r.status_code}")

        by_symbol: dict[str, list[PriceRow]] = {s.upper(): [] for s in symbols}
        for item in r.json().get("data", []):
            sym = item.get("symbol", "").upper()
            raw_date = item.get("date", "")
            raw_close = item.get("close")
            if not (sym in by_symbol and raw_date and raw_close is not None):
                continue
            close = float(raw_close)
            if close > 0:
                adj_close = _valid_adj_close(item.get("adj_close"))
                by_symbol[sym].append(
                    PriceRow(date=raw_date[:10], close=close, adj_close=adj_close)
                )

        return {sym: rows[-days:] for sym, rows in by_symbol.items()}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_intraday_candles(self, symbol: str, limit: int = 260) -> list["IntradayCandle"]:
        """Marketstack's /intraday endpoint already returns official 30-min bars,
        so each row becomes a candle directly (sample_count=1, quality "ok") rather
        than going through client-side bucketing."""
        from app.services.intraday import IntradayCandle

        log_provider_call("marketstack", "intraday", symbols=1, limit=limit)
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{self.BASE}/intraday",
                params={
                    "access_key": self.api_key,
                    "symbols": symbol.upper(),
                    "interval": "30min",
                    "limit": limit,
                    "sort": "ASC",
                },
            )

        if r.status_code == 429:
            raise ProviderError(429, "Marketstack rate limited on intraday")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"Marketstack intraday error {r.status_code}")

        candles: list[IntradayCandle] = []
        for item in r.json().get("data", []):
            raw_date = item.get("date", "")
            o, h, low, c = item.get("open"), item.get("high"), item.get("low"), item.get("close")
            if not raw_date or None in (o, h, low, c):
                continue
            if any(float(v) <= 0 for v in (o, h, low, c)):
                continue
            bucket_ts = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            candles.append(IntradayCandle(
                bucket_ts=bucket_ts,
                open=float(o), high=float(h), low=float(low), close=float(c),
                sample_count=1,
                data_quality="ok",
            ))
        return candles
