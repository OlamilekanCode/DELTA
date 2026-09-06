"""Tests for AssetQuote seeding and the quote fields returned by /assets endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crypto_asset_has_quote_fields(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/BTC")
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_type"] == "crypto"
    assert body["last_price"] is not None
    assert body["change_24h_pct"] is not None
    assert body["market_cap_usd"] is not None
    assert body["volume_24h_usd"] is not None
    assert body["quote_provider"] == "fixture"
    assert body["quote_ts"] is not None


@pytest.mark.asyncio
async def test_crypto_asset_change_in_valid_range(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/ETH")
    body = resp.json()
    chg = body["change_24h_pct"]
    assert chg is not None
    assert -100 < chg < 100, f"change_24h_pct={chg} is out of expected range"


@pytest.mark.asyncio
async def test_stock_asset_has_no_quote_fields(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/NVDA")
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_type"] == "stock"
    assert body["last_price"] is not None
    assert body["change_24h_pct"] is None
    assert body["market_cap_usd"] is None
    assert body["volume_24h_usd"] is None
    assert body["quote_provider"] is None


@pytest.mark.asyncio
async def test_asset_list_crypto_has_change_pct(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets?type=crypto")
    assert resp.status_code == 200
    for a in resp.json()["assets"]:
        assert a["change_24h_pct"] is not None, f"{a['symbol']} missing change_24h_pct"
        assert a["market_cap_usd"] is not None, f"{a['symbol']} missing market_cap_usd"


@pytest.mark.asyncio
async def test_asset_list_stocks_have_no_change_pct(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets?type=stock")
    assert resp.status_code == 200
    for a in resp.json()["assets"]:
        assert a["change_24h_pct"] is None, f"{a['symbol']} should not have change_24h_pct"


@pytest.mark.asyncio
async def test_search_crypto_has_quote_data(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/search?q=bitcoin")
    assert resp.status_code == 200
    assets = resp.json()["assets"]
    btc = next((a for a in assets if a["symbol"] == "BTC"), None)
    assert btc is not None
    assert btc["change_24h_pct"] is not None
    assert btc["market_cap_usd"] is not None


@pytest.mark.asyncio
async def test_pepe_quote_price_is_small(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/assets/PEPE")
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_price"] is not None
    assert 0 < body["last_price"] < 1, "PEPE price should be less than $1"
