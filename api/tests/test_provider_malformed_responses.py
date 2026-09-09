"""An unparseable/unexpected-shape provider response must raise, never
return an empty list — the portfolio catalogue sync treats an empty list
as "confirmed: nothing exists upstream anymore" and deactivates every
previously-synced row from that source. A malformed response must be
indistinguishable from any other fetch failure (preserve existing rows).
"""

import pytest

from app.providers.base import ProviderError
from app.providers.coingecko import CoinGeckoProvider
from app.providers.robinhood import RobinhoodAssetProvider


@pytest.mark.asyncio
async def test_coingecko_coins_list_raises_on_non_list_response(httpx_mock) -> None:
    # Both providers retry up to 3 times on ProviderError before giving up.
    for _ in range(3):
        httpx_mock.add_response(
            url="https://api.coingecko.com/api/v3/coins/list?include_platform=true",
            json={"error": "unexpected shape"},
        )
    provider = CoinGeckoProvider("test-key")
    with pytest.raises(ProviderError):
        await provider.fetch_coins_list_with_platforms()


@pytest.mark.asyncio
async def test_robinhood_asset_registry_raises_on_non_list_response(httpx_mock) -> None:
    for _ in range(3):
        httpx_mock.add_response(
            url="https://api.robinhood.com/rhj/assets",
            json={"unexpected": "shape"},
        )
    provider = RobinhoodAssetProvider()
    with pytest.raises(ProviderError):
        await provider.fetch_stock_tokens()
