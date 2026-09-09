"""Robinhood Stock Token asset registry client.

Fetches Robinhood's public tokenized-equity asset list so the portfolio
catalogue sync can resolve verified on-chain contract addresses for our
tracked stock symbols on Robinhood Chain.

The exact response schema of `https://api.robinhood.com/rhj/assets` has not
been reconfirmed against a live response as of this writing — field names
below (`symbol`, `chain_id`, `contract_address`, `decimals`, `status`,
`multiplier`) are a best-effort reading of the fields Robinhood's own
tokenized-stock documentation describes, not a guarantee. Every field is
read defensively with `.get()`; a response that doesn't match drops that
entry (or, if the whole payload is unparseable, returns an empty list)
rather than crashing the sync or fabricating a contract address. This must
be reconfirmed against a live response before this sync is relied on in
production — see cmd_refresh_portfolio_catalogue's docstring.
"""

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.providers.base import ProviderError
from app.services.provider_usage import log_provider_call

log = logging.getLogger(__name__)


class RobinhoodStockToken:
    def __init__(
        self,
        symbol: str,
        chain_id: int,
        contract_address: str,
        decimals: int,
        active: bool,
        current_multiplier: float | None,
    ) -> None:
        self.symbol = symbol
        self.chain_id = chain_id
        self.contract_address = contract_address
        self.decimals = decimals
        self.active = active
        self.current_multiplier = current_multiplier


class RobinhoodAssetProvider:
    BASE = "https://api.robinhood.com/rhj/assets"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def fetch_stock_tokens(self) -> list[RobinhoodStockToken]:
        log_provider_call("robinhood", "assets", assets=0)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(self.BASE)

        if r.status_code == 429:
            raise ProviderError(429, "Robinhood asset registry rate limited")

        if r.status_code != 200:
            raise ProviderError(r.status_code, f"Robinhood asset registry error {r.status_code}")

        body = r.json()
        raw_items = body.get("results", body) if isinstance(body, dict) else body
        if not isinstance(raw_items, list):
            log.warning("Robinhood asset registry response was not a list — skipping this sync")
            return []

        tokens: list[RobinhoodStockToken] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol") or item.get("ticker")
            chain_id = item.get("chain_id") or item.get("chainId")
            contract_address = item.get("contract_address") or item.get("token_address") or item.get("address")
            if not symbol or chain_id is None or not contract_address:
                continue
            try:
                chain_id_int = int(chain_id)
            except (TypeError, ValueError):
                continue
            decimals_raw = item.get("decimals")
            try:
                decimals = int(decimals_raw) if decimals_raw is not None else 18
            except (TypeError, ValueError):
                decimals = 18
            status = (item.get("status") or item.get("state") or "").lower()
            active = bool(item.get("active", status in ("active", "live", "")))
            multiplier_raw = item.get("current_multiplier") or item.get("currentMultiplier")
            try:
                current_multiplier = float(multiplier_raw) if multiplier_raw is not None else None
            except (TypeError, ValueError):
                current_multiplier = None
            tokens.append(RobinhoodStockToken(
                symbol=str(symbol).upper(),
                chain_id=chain_id_int,
                contract_address=str(contract_address).lower(),
                decimals=decimals,
                active=active,
                current_multiplier=current_multiplier,
            ))
        return tokens
