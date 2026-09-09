from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.quote import AssetQuote
from app.models.wallet_position import CachedWalletPosition
from app.services.blockchain import MockRpcProvider
from app.services.portfolio import (
    TIER_THRESHOLDS,
    compute_portfolio_exposure,
    get_tier,
    refresh_wallet_positions,
    shape_portfolio_response,
)
from app.services.portfolio_assets import NATIVE, PortfolioAssetContract


def test_tier_boundary_locked_below_50() -> None:
    assert get_tier(4_999) == "locked"


def test_tier_boundary_exactly_50_is_summary() -> None:
    assert get_tier(5_000) == "summary"


def test_tier_boundary_just_under_250_is_summary() -> None:
    assert get_tier(24_999) == "summary"


def test_tier_boundary_exactly_250_is_detailed() -> None:
    assert get_tier(25_000) == "detailed"


def test_tier_boundary_just_under_1000_is_detailed() -> None:
    assert get_tier(99_999) == "detailed"


def test_tier_boundary_exactly_1000_is_premium() -> None:
    assert get_tier(100_000) == "premium"


def test_tier_boundary_well_above_1000_is_premium() -> None:
    assert get_tier(10_000_000) == "premium"


def test_tier_zero_is_locked() -> None:
    assert get_tier(0) == "locked"


def test_thresholds_match_dollar_amounts() -> None:
    assert TIER_THRESHOLDS["summary"] == 5_000  # $50.00
    assert TIER_THRESHOLDS["detailed"] == 25_000  # $250.00
    assert TIER_THRESHOLDS["premium"] == 100_000  # $1,000.00


def test_shape_summary_strips_holdings_and_per_stock_data() -> None:
    exposure = {
        "ranked": [
            {"stock": "TSLA", "portfolio_exposure_score": -0.9, "assets": [{"symbol": "BTC", "weight": 0.5, "score": -0.9}]},
            {"stock": "NVDA", "portfolio_exposure_score": 0.3, "assets": [{"symbol": "BTC", "weight": 0.5, "score": 0.3}]},
        ],
        "assets": [{"symbol": "BTC", "weight": 1.0}],
        "category_exposure": [{"category": "Layer 1", "weight": 1.0}],
        "excluded": [{"symbol": "ETH", "reason": "missing_price"}],
        "data_ts": "2026-01-01T00:00:00+00:00",
    }
    shaped = shape_portfolio_response("summary", exposure)
    assert shaped["portfolio_exposure_score"] == pytest.approx(-0.3, rel=1e-3)
    assert shaped["stocks_covered"] == 2
    assert "assets" not in shaped
    assert "excluded" not in shaped
    assert "ranked" not in shaped
    assert "category_exposure" not in shaped


def test_shape_summary_single_stock_query_hides_contributions() -> None:
    exposure = {
        "stock": "NVDA",
        "portfolio_exposure_score": 0.42,
        "assets": [{"symbol": "BTC", "weight": 1.0, "score": 0.42}],
        "excluded": [],
        "data_ts": None,
    }
    shaped = shape_portfolio_response("summary", exposure)
    assert shaped == {"portfolio_exposure_score": 0.42, "stocks_covered": 1, "data_ts": None}


def test_shape_detailed_passes_through_unchanged() -> None:
    exposure = {"ranked": [], "assets": [], "category_exposure": [], "excluded": [], "data_ts": None}
    assert shape_portfolio_response("detailed", exposure) == exposure


def test_shape_premium_adds_coming_soon_on_top_of_detailed() -> None:
    exposure = {"ranked": [], "assets": [], "category_exposure": [], "excluded": [], "data_ts": None}
    shaped = shape_portfolio_response("premium", exposure)
    assert shaped["ranked"] == []
    assert set(shaped["coming_soon"]) == {"advanced_graphs", "longer_portfolio_history", "alerts"}


def test_shape_passes_through_error_regardless_of_tier() -> None:
    exposure = {"error": "unknown_stock", "portfolio_exposure_score": None, "assets": []}
    assert shape_portfolio_response("summary", exposure) == exposure


WALLET = "0x" + "1" * 40


async def _seed_quote(db: AsyncSession, symbol: str, price_usd: float) -> Asset:
    asset = (await db.execute(select(Asset).where(Asset.symbol == symbol))).scalar_one()
    existing = (await db.execute(select(AssetQuote).where(AssetQuote.asset_id == asset.id))).scalar_one_or_none()
    if existing:
        existing.price_usd = price_usd
    else:
        db.add(AssetQuote(asset_id=asset.id, price_usd=price_usd, market_cap_usd=None,
                           volume_24h_usd=None, change_24h_pct=None, ts=datetime.now(UTC),
                           provider="test", is_demo=True))
    await db.commit()
    return asset


async def _seed_position(db: AsyncSession, symbol: str, quantity: float, decimals: int = 18) -> None:
    asset = (await db.execute(select(Asset).where(Asset.symbol == symbol))).scalar_one()
    db.add(CachedWalletPosition(
        wallet_address=WALLET.lower(), chain_id=8453, contract_address=f"0x{symbol.lower():0<40}",
        asset_id=asset.id, quantity_raw=str(int(quantity * 10**decimals)), decimals=decimals,
        block_number=1, updated_at=datetime.now(UTC),
    ))
    await db.commit()


async def _seed_score(db: AsyncSession, stock_symbol: str, crypto_symbol: str, score: float) -> None:
    """Overwrite (not insert alongside) the pair's score — the `db` fixture
    already runs recompute_all_scores once, so every stock/crypto pair has an
    existing fixture-derived row."""
    stock = (await db.execute(select(Asset).where(Asset.symbol == stock_symbol, Asset.asset_type == "stock"))).scalar_one()
    crypto = (await db.execute(select(Asset).where(Asset.symbol == crypto_symbol))).scalar_one()
    existing = (await db.execute(
        select(StoredExposureScore).where(
            StoredExposureScore.stock_id == stock.id, StoredExposureScore.crypto_id == crypto.id
        )
    )).scalar_one_or_none()
    if existing:
        existing.score = score
        existing.raw_correlation = score
        existing.computed_at = datetime.now(UTC)
    else:
        db.add(StoredExposureScore(
            stock_id=stock.id, crypto_id=crypto.id, score=score, raw_correlation=score,
            observations=90, computed_at=datetime.now(UTC), model_version="v1", is_demo=True,
        ))
    await db.commit()


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_no_positions_returns_honest_empty(db: AsyncSession) -> None:
    result = await compute_portfolio_exposure(db, WALLET)
    assert result["portfolio_exposure_score"] is None
    assert result["assets"] == []


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_weights_sum_to_one(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_quote(db, "ETH", 4_000.0)
    await _seed_position(db, "BTC", 1.0)  # $100,000
    await _seed_position(db, "ETH", 25.0)  # $100,000 — equal weight

    result = await compute_portfolio_exposure(db, WALLET)
    weights = {a["symbol"]: a["weight"] for a in result["assets"]}
    assert weights["BTC"] == pytest.approx(0.5, rel=1e-3)
    assert weights["ETH"] == pytest.approx(0.5, rel=1e-3)


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_signed_weighted_score(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_quote(db, "ETH", 4_000.0)
    await _seed_position(db, "BTC", 1.0)  # $100,000
    await _seed_position(db, "ETH", 25.0)  # $100,000
    await _seed_score(db, "NVDA", "BTC", 0.8)
    await _seed_score(db, "NVDA", "ETH", -0.4)

    result = await compute_portfolio_exposure(db, WALLET, stock_symbol="NVDA")
    # 0.5 * 0.8 + 0.5 * -0.4 = 0.2
    assert result["portfolio_exposure_score"] == pytest.approx(0.2, rel=1e-3)


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_fresh_data_not_stale(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_position(db, "BTC", 1.0)

    result = await compute_portfolio_exposure(db, WALLET)
    assert result["positions_stale"] is False
    assert result["quotes_stale"] is False
    assert result["total_usd_value"] == pytest.approx(100_000.0, rel=1e-6)
    assert result["supported_position_count"] == 1
    assert result["excluded_position_count"] == 0


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_stale_positions_flagged(db: AsyncSession) -> None:
    """A cached position snapshot old enough to be stale must be clearly
    flagged, not silently presented as current."""
    await _seed_quote(db, "BTC", 100_000.0)
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    db.add(CachedWalletPosition(
        wallet_address=WALLET.lower(), chain_id=8453, contract_address="0xbtc",
        asset_id=btc.id, quantity_raw=str(10**18), decimals=18,
        block_number=1, updated_at=datetime.now(UTC) - timedelta(hours=2),
    ))
    await db.commit()

    result = await compute_portfolio_exposure(db, WALLET)
    assert result["positions_stale"] is True


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_stale_quotes_flagged(db: AsyncSession) -> None:
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    existing_quote = (await db.execute(select(AssetQuote).where(AssetQuote.asset_id == btc.id))).scalar_one_or_none()
    if existing_quote:
        await db.delete(existing_quote)
        await db.commit()
    db.add(AssetQuote(
        asset_id=btc.id, price_usd=100_000.0, market_cap_usd=None, volume_24h_usd=None,
        change_24h_pct=None, ts=datetime.now(UTC) - timedelta(hours=2), provider="test", is_demo=True,
    ))
    await db.commit()
    await _seed_position(db, "BTC", 1.0)  # fresh position, stale quote

    result = await compute_portfolio_exposure(db, WALLET)
    assert result["positions_stale"] is False
    assert result["quotes_stale"] is True


@pytest.mark.asyncio
async def test_shape_summary_passes_through_staleness_and_coverage(db: AsyncSession) -> None:
    exposure = {
        "ranked": [{"stock": "NVDA", "portfolio_exposure_score": 0.5, "assets": []}],
        "positions_stale": True,
        "quotes_stale": False,
        "total_usd_value": 42.0,
        "data_ts": None,
    }
    shaped = shape_portfolio_response("summary", exposure)
    assert shaped["positions_stale"] is True
    assert shaped["quotes_stale"] is False
    assert shaped["total_usd_value"] == 42.0
    assert "assets" not in shaped  # still no detailed holdings at summary tier


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_missing_price_excluded(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_position(db, "BTC", 1.0)

    # Fixture seeding gives every crypto asset a quote — remove ETH's so this
    # test actually exercises the missing-price path.
    eth_asset = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()
    existing_quote = (await db.execute(select(AssetQuote).where(AssetQuote.asset_id == eth_asset.id))).scalar_one_or_none()
    if existing_quote:
        await db.delete(existing_quote)
        await db.commit()

    db.add(CachedWalletPosition(
        wallet_address=WALLET.lower(), chain_id=8453, contract_address="0xeth",
        asset_id=eth_asset.id, quantity_raw=str(10**18), decimals=18,
        block_number=1, updated_at=datetime.now(UTC),
    ))
    await db.commit()

    result = await compute_portfolio_exposure(db, WALLET)
    excluded_symbols = {e.get("symbol") for e in result["excluded"]}
    assert "ETH" in excluded_symbols
    weights = {a["symbol"] for a in result["assets"]}
    assert weights == {"BTC"}


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_unsupported_token_excluded(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_position(db, "BTC", 1.0)
    db.add(CachedWalletPosition(
        wallet_address=WALLET.lower(), chain_id=8453, contract_address="0xunsupported",
        asset_id=None, quantity_raw="1000000000000000000", decimals=18,
        block_number=1, updated_at=datetime.now(UTC),
    ))
    await db.commit()

    result = await compute_portfolio_exposure(db, WALLET)
    reasons = {e["reason"] for e in result["excluded"]}
    assert "unsupported_token" in reasons


@pytest.mark.asyncio
async def test_compute_portfolio_exposure_ranked_summary_sorted_by_magnitude(db: AsyncSession) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    await _seed_position(db, "BTC", 1.0)
    await _seed_score(db, "NVDA", "BTC", 0.3)
    await _seed_score(db, "TSLA", "BTC", -0.9)

    result = await compute_portfolio_exposure(db, WALLET)
    ranked_stocks = [r["stock"] for r in result["ranked"]]
    assert ranked_stocks[0] == "TSLA"  # |-0.9| > |0.3|


@pytest.mark.asyncio
async def test_refresh_wallet_positions_reads_native_and_erc20(db: AsyncSession, monkeypatch) -> None:
    import app.services.portfolio as portfolio_module

    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()
    contracts = [
        PortfolioAssetContract(chain_id=8453, contract_address=NATIVE, decimals=18, symbol="ETH"),
        PortfolioAssetContract(chain_id=8453, contract_address="0xbtccontract", decimals=8, symbol="BTC"),
    ]
    monkeypatch.setattr(portfolio_module, "contracts_for_chain", lambda chain_id: contracts if chain_id == 8453 else [])

    from app.config import Settings
    settings = Settings(portfolio_chain_ids="8453", database_url="sqlite+aiosqlite:///./test.db")
    monkeypatch.setattr(portfolio_module, "get_settings", lambda: settings)

    mock = MockRpcProvider(
        chain_id=8453,
        block_number=42,
        native_balances={WALLET.lower(): 5 * 10**18},
        balances={("0xbtccontract", WALLET.lower()): 2 * 10**8},
    )
    result = await refresh_wallet_positions(db, WALLET, rpc_by_chain={8453: mock})
    assert result.status == "ok"
    assert result.chains_attempted == 1
    assert result.contracts_attempted == 2
    assert result.positions_refreshed == 2
    assert result.skipped == 0
    assert result.failed == 0

    rows = (await db.execute(select(CachedWalletPosition).where(CachedWalletPosition.wallet_address == WALLET.lower()))).scalars().all()
    by_contract = {r.contract_address: r for r in rows}
    assert by_contract[NATIVE].quantity_raw == str(5 * 10**18)
    assert by_contract["0xbtccontract"].quantity_raw == str(2 * 10**8)
    assert by_contract["0xbtccontract"].asset_id == btc.id
    assert by_contract[NATIVE].block_number == 42


@pytest.mark.asyncio
async def test_refresh_wallet_positions_skips_chains_without_rpc(db: AsyncSession, monkeypatch) -> None:
    import app.services.portfolio as portfolio_module

    contracts = [PortfolioAssetContract(chain_id=1, contract_address=NATIVE, decimals=18, symbol="ETH")]
    monkeypatch.setattr(portfolio_module, "contracts_for_chain", lambda chain_id: contracts if chain_id == 1 else [])

    from app.config import Settings
    settings = Settings(portfolio_chain_ids="1", database_url="sqlite+aiosqlite:///./test.db")
    monkeypatch.setattr(portfolio_module, "get_settings", lambda: settings)

    # No RPC provided for chain 1 at all — nothing usable is configured.
    result = await refresh_wallet_positions(db, WALLET, rpc_by_chain={})
    assert result.status == "not_configured"
    assert result.positions == []


@pytest.mark.asyncio
async def test_refresh_wallet_positions_skips_one_chain_when_another_is_configured(db: AsyncSession, monkeypatch) -> None:
    """Chain 1 has contracts but no RPC; chain 8453 has both — chain 1's
    contracts must be counted as skipped, not silently dropped, while
    chain 8453 still refreshes normally."""
    import app.services.portfolio as portfolio_module

    contracts_by_chain = {
        1: [PortfolioAssetContract(chain_id=1, contract_address=NATIVE, decimals=18, symbol="ETH")],
        8453: [PortfolioAssetContract(chain_id=8453, contract_address=NATIVE, decimals=18, symbol="ETH")],
    }
    monkeypatch.setattr(portfolio_module, "contracts_for_chain", lambda chain_id: contracts_by_chain.get(chain_id, []))

    from app.config import Settings
    settings = Settings(portfolio_chain_ids="1,8453", database_url="sqlite+aiosqlite:///./test.db")
    monkeypatch.setattr(portfolio_module, "get_settings", lambda: settings)

    mock = MockRpcProvider(chain_id=8453, block_number=1, native_balances={WALLET.lower(): 1})
    result = await refresh_wallet_positions(db, WALLET, rpc_by_chain={8453: mock})
    assert result.status == "ok"
    assert result.chains_attempted == 2
    assert result.contracts_attempted == 2
    assert result.positions_refreshed == 1
    assert result.skipped == 1


@pytest.mark.asyncio
async def test_refresh_wallet_positions_distrusts_wrong_chain_id(db: AsyncSession, monkeypatch) -> None:
    """An RPC that reports back a chain ID different from the one it was
    registered for must never have its balances trusted."""
    import app.services.portfolio as portfolio_module

    contracts = [PortfolioAssetContract(chain_id=8453, contract_address=NATIVE, decimals=18, symbol="ETH")]
    monkeypatch.setattr(portfolio_module, "contracts_for_chain", lambda chain_id: contracts if chain_id == 8453 else [])

    from app.config import Settings
    settings = Settings(portfolio_chain_ids="8453", database_url="sqlite+aiosqlite:///./test.db")
    monkeypatch.setattr(portfolio_module, "get_settings", lambda: settings)

    # Misconfigured/wrong RPC: registered under chain 8453 but actually chain 1.
    mock = MockRpcProvider(chain_id=1, block_number=1, native_balances={WALLET.lower(): 5 * 10**18})
    result = await refresh_wallet_positions(db, WALLET, rpc_by_chain={8453: mock})
    assert result.status == "ok"
    assert result.failed == 1
    assert result.positions_refreshed == 0
    assert result.positions == []


@pytest.mark.asyncio
async def test_refresh_wallet_positions_not_configured_with_empty_catalogue(db: AsyncSession) -> None:
    """The real production contract catalogue is empty until addresses are
    confirmed — refresh must say so explicitly rather than report a
    misleading zero-position success."""
    result = await refresh_wallet_positions(db, WALLET)
    assert result.status == "not_configured"
    assert result.positions_refreshed == 0


@pytest.mark.asyncio
async def test_refresh_wallet_positions_preserves_cache_on_rpc_failure(db: AsyncSession, monkeypatch) -> None:
    import app.services.portfolio as portfolio_module

    contracts = [PortfolioAssetContract(chain_id=8453, contract_address=NATIVE, decimals=18, symbol="ETH")]
    monkeypatch.setattr(portfolio_module, "contracts_for_chain", lambda chain_id: contracts if chain_id == 8453 else [])

    from app.config import Settings
    settings = Settings(portfolio_chain_ids="8453", database_url="sqlite+aiosqlite:///./test.db")
    monkeypatch.setattr(portfolio_module, "get_settings", lambda: settings)

    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()
    db.add(CachedWalletPosition(
        wallet_address=WALLET.lower(), chain_id=8453, contract_address=NATIVE,
        asset_id=eth.id, quantity_raw=str(9 * 10**18), decimals=18,
        block_number=10, updated_at=datetime.now(UTC),
    ))
    await db.commit()

    mock = MockRpcProvider(chain_id=8453, raise_on_call=Exception("rpc down"))
    result = await refresh_wallet_positions(db, WALLET, rpc_by_chain={8453: mock})
    assert result.status == "ok"
    assert result.failed == 1

    row = (await db.execute(
        select(CachedWalletPosition).where(CachedWalletPosition.wallet_address == WALLET.lower())
    )).scalar_one()
    assert row.quantity_raw == str(9 * 10**18)  # untouched by the failed refresh


# ── GET /api/v1/portfolio/exposure — server-side tier enforcement ──────────
# Proves a summary-tier caller cannot retrieve detailed fields by calling the
# API directly, regardless of what the frontend would or wouldn't render.

_TEST_CHAIN_ID = 8453
_TOKEN_ADDRESS = "0x" + "9" * 40


def _entitlement_settings():
    from app.config import Settings

    return Settings(
        cors_origins="http://localhost:3000",
        synthex_chain_id=_TEST_CHAIN_ID,
        synthex_token_address=_TOKEN_ADDRESS,
        database_url="sqlite+aiosqlite:///./test.db",
    )


async def _authenticated_holder(client, db: AsyncSession, monkeypatch, tier: str, cumulative_usd_cents: int) -> dict:
    """Authenticate a fresh wallet, mark it a verified holder, and give it a
    persisted entitlement at the given tier — mirroring how a real verified
    purchase would set `wallet_entitlements`."""
    from datetime import timedelta

    from eth_account import Account
    from eth_account.messages import encode_defunct

    from app.models.auth import CachedWalletBalance
    from app.models.portfolio import WalletEntitlement
    from app.services import auth as auth_service
    from app.services import holder as holder_service

    settings = _entitlement_settings()
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(holder_service, "get_settings", lambda: settings)

    r = await client.post("/api/v1/auth/nonce")
    nonce = r.json()["nonce"]
    account = Account.create()
    now = datetime.now(UTC)
    message = (
        "localhost:3000 wants you to sign in with your Ethereum account:\n"
        f"{account.address}\n\nSign in to Synthetic Exposure.\n\n"
        "URI: http://localhost:3000\nVersion: 1\n"
        f"Chain ID: {_TEST_CHAIN_ID}\nNonce: {nonce}\n"
        f"Issued At: {now.isoformat()}\nExpiration Time: {(now + timedelta(minutes=10)).isoformat()}\n"
    )
    signature = account.sign_message(encode_defunct(text=message)).signature.hex()
    r = await client.post("/api/v1/auth/verify", json={"message": message, "signature": signature})
    body = r.json()
    wallet = body["wallet_address"]

    db.add(CachedWalletBalance(
        wallet_address=wallet, token_address=_TOKEN_ADDRESS.lower(),
        balance_raw="1000000000000000000000", checked_at=datetime.now(UTC), is_holder=True,
    ))
    db.add(WalletEntitlement(
        wallet_address=wallet, tier=tier, cumulative_usd_cents=cumulative_usd_cents, updated_at=datetime.now(UTC),
    ))
    await db.commit()

    return {"Authorization": f"Bearer {body['session_token']}"}, wallet


async def _seed_position_for(db: AsyncSession, wallet: str, symbol: str, quantity: float, decimals: int = 18) -> None:
    asset = (await db.execute(select(Asset).where(Asset.symbol == symbol))).scalar_one()
    db.add(CachedWalletPosition(
        wallet_address=wallet.lower(), chain_id=8453, contract_address=f"0x{symbol.lower():0<40}",
        asset_id=asset.id, quantity_raw=str(int(quantity * 10**decimals)), decimals=decimals,
        block_number=1, updated_at=datetime.now(UTC),
    ))
    await db.commit()


@pytest.mark.asyncio
async def test_summary_tier_cannot_retrieve_detailed_fields_via_api(client, db: AsyncSession, monkeypatch) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    headers, wallet = await _authenticated_holder(client, db, monkeypatch, tier="summary", cumulative_usd_cents=5_000)
    await _seed_position_for(db, wallet, "BTC", 1.0)

    r = await client.get("/api/v1/portfolio/exposure", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "summary"
    assert "portfolio_exposure_score" in body
    for detailed_field in ("assets", "excluded", "ranked", "category_exposure"):
        assert detailed_field not in body, f"summary tier leaked detailed field {detailed_field!r}"


@pytest.mark.asyncio
async def test_detailed_tier_receives_full_fields_via_api(client, db: AsyncSession, monkeypatch) -> None:
    await _seed_quote(db, "BTC", 100_000.0)
    headers, wallet = await _authenticated_holder(client, db, monkeypatch, tier="detailed", cumulative_usd_cents=25_000)
    await _seed_position_for(db, wallet, "BTC", 1.0)

    r = await client.get("/api/v1/portfolio/exposure", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "detailed"
    assert "assets" in body
    assert "excluded" in body
    assert "category_exposure" in body


@pytest.mark.asyncio
async def test_locked_tier_returns_no_analysis_data(client, db: AsyncSession, monkeypatch) -> None:
    headers, _wallet = await _authenticated_holder(client, db, monkeypatch, tier="locked", cumulative_usd_cents=0)
    r = await client.get("/api/v1/portfolio/exposure", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["tier"] == "locked"
    for field_name in ("assets", "excluded", "ranked", "portfolio_exposure_score"):
        assert field_name not in body
