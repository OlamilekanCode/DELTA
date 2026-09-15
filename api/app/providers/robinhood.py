"""Robinhood Stock Token asset registry client.

Fetches Robinhood's public tokenized-equity asset list so the portfolio
catalogue sync can resolve verified on-chain contract addresses for our
tracked stock symbols on Robinhood Chain.

Response schema confirmed 2026-09-15 against a live response from
`https://api.robinhood.com/rhj/assets`:

    {"assets": [
        {"tokenSymbol": "CRM", "tokenName": "...",
         "deployments": [{"contractAddress": "0x...", "chainId": 4663,
                           "networkName": "Robinhood Chain"}],
         "currentMultiplier": "1.000000000000000000", "pendingMultiplier": "",
         "status": "ASSET_STATUS_ACTIVE", "tokenDecimals": 18, ...},
        ...
    ]}

One asset can have deployments on more than one chain, so each deployment
becomes its own RobinhoodStockToken — sync_robinhood_stock_tokens (see
services/portfolio_catalog.py) filters to ROBINHOOD_CHAIN_ID itself. Every
field is still read defensively with `.get()`; a response that doesn't match
drops that entry (or, if the whole payload is unparseable, raises rather
than returning an empty list — see the ProviderError below) rather than
crashing the sync or fabricating a contract address.
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


_ACTIVE_STATUSES = {"ASSET_STATUS_ACTIVE"}


def _parse_active(status: str) -> bool:
    """Fails closed (inactive) on anything ambiguous or unrecognized — a
    token must never be treated as active by accident. The live API has no
    separate boolean `active` field, only this `status` enum string."""
    return status in _ACTIVE_STATUSES


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
        raw_items = body.get("assets", body) if isinstance(body, dict) else body
        if not isinstance(raw_items, list):
            # Must raise, never return [] — the sync layer treats an empty
            # list as "confirmed: nothing exists upstream anymore" and
            # deactivates every previously-synced row from this source. An
            # unparseable response is not that; it must be indistinguishable
            # from any other fetch failure (preserve existing rows).
            raise ProviderError(0, "Robinhood asset registry response was not a list")

        tokens: list[RobinhoodStockToken] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            symbol = item.get("tokenSymbol")
            deployments = item.get("deployments")
            if not symbol or not isinstance(deployments, list):
                continue
            decimals_raw = item.get("tokenDecimals")
            try:
                decimals = int(decimals_raw) if decimals_raw is not None else 18
            except (TypeError, ValueError):
                decimals = 18
            active = _parse_active(str(item.get("status") or ""))
            multiplier_raw = item.get("currentMultiplier")
            try:
                current_multiplier = float(multiplier_raw) if multiplier_raw else None
            except (TypeError, ValueError):
                current_multiplier = None

            # One asset can be deployed on more than one chain — each
            # deployment is its own token; sync_robinhood_stock_tokens
            # filters down to ROBINHOOD_CHAIN_ID itself.
            for deployment in deployments:
                if not isinstance(deployment, dict):
                    continue
                chain_id = deployment.get("chainId")
                contract_address = deployment.get("contractAddress")
                if chain_id is None or not contract_address:
                    continue
                try:
                    chain_id_int = int(chain_id)
                except (TypeError, ValueError):
                    continue
                tokens.append(RobinhoodStockToken(
                    symbol=str(symbol).upper(),
                    chain_id=chain_id_int,
                    contract_address=str(contract_address).lower(),
                    decimals=decimals,
                    active=active,
                    current_multiplier=current_multiplier,
                ))
        return tokens
