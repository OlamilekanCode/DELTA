"""providers/robinhood.py — _parse_active fails closed on anything ambiguous,
and fetch_stock_tokens parses the real live response shape.

The live API (confirmed 2026-09-15) has no separate boolean `active` field,
only a `status` enum string (e.g. "ASSET_STATUS_ACTIVE") — a token's active
status must never default to True on an unrecognized or empty value.
"""

import pytest

from app.providers.robinhood import RobinhoodAssetProvider, _parse_active


def test_active_status_is_active() -> None:
    assert _parse_active("ASSET_STATUS_ACTIVE") is True


def test_inactive_status_is_not_active() -> None:
    assert _parse_active("ASSET_STATUS_INACTIVE") is False


def test_unrecognized_status_defaults_inactive() -> None:
    assert _parse_active("ASSET_STATUS_DELISTED") is False


def test_empty_status_defaults_inactive() -> None:
    """An empty/missing status must fail closed (inactive), never default
    to active."""
    assert _parse_active("") is False


@pytest.mark.asyncio
async def test_fetch_stock_tokens_parses_live_response_shape(httpx_mock) -> None:
    """Real shape confirmed 2026-09-15: top-level "assets" list, tokenSymbol,
    a "deployments" list (chainId/contractAddress per chain), tokenDecimals,
    and a status enum string — not the earlier "results"/symbol/chain_id/
    contract_address/decimals/active guess."""
    httpx_mock.add_response(
        url="https://api.robinhood.com/rhj/assets",
        json={"assets": [
            {
                "tokenSymbol": "CRM",
                "tokenName": "Salesforce • Robinhood Token",
                "deployments": [
                    {"contractAddress": "0xD95B44124E475743A7589E68F3D74008A5536D44",
                     "chainId": 4663, "networkName": "Robinhood Chain"},
                ],
                "currentMultiplier": "1.000000000000000000",
                "pendingMultiplier": "",
                "status": "ASSET_STATUS_ACTIVE",
                "tokenDecimals": 18,
            },
            {
                # Delisted — must be parsed but marked inactive, not dropped.
                "tokenSymbol": "OLD",
                "deployments": [
                    {"contractAddress": "0x1111111111111111111111111111111111111", "chainId": 4663},
                ],
                "currentMultiplier": "1.000000000000000000",
                "status": "ASSET_STATUS_DELISTED",
                "tokenDecimals": 18,
            },
        ]},
    )
    provider = RobinhoodAssetProvider()
    tokens = await provider.fetch_stock_tokens()

    assert len(tokens) == 2
    crm = next(t for t in tokens if t.symbol == "CRM")
    assert crm.chain_id == 4663
    assert crm.contract_address == "0xd95b44124e475743a7589e68f3d74008a5536d44"
    assert crm.decimals == 18
    assert crm.active is True
    assert crm.current_multiplier == 1.0

    old = next(t for t in tokens if t.symbol == "OLD")
    assert old.active is False


@pytest.mark.asyncio
async def test_fetch_stock_tokens_fans_out_multiple_deployments(httpx_mock) -> None:
    """One asset deployed on more than one chain becomes one token per
    deployment — the sync layer filters down to ROBINHOOD_CHAIN_ID itself."""
    httpx_mock.add_response(
        url="https://api.robinhood.com/rhj/assets",
        json={"assets": [
            {
                "tokenSymbol": "CRM",
                "deployments": [
                    {"contractAddress": "0xaaaa000000000000000000000000000000000a", "chainId": 4663},
                    {"contractAddress": "0xbbbb000000000000000000000000000000000b", "chainId": 1},
                ],
                "status": "ASSET_STATUS_ACTIVE",
                "tokenDecimals": 18,
            },
        ]},
    )
    provider = RobinhoodAssetProvider()
    tokens = await provider.fetch_stock_tokens()

    assert {t.chain_id for t in tokens} == {4663, 1}
    assert all(t.symbol == "CRM" for t in tokens)
