from datetime import UTC, datetime

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
        block_number=42,
        native_balances={WALLET.lower(): 5 * 10**18},
        balances={("0xbtccontract", WALLET.lower()): 2 * 10**8},
    )
    positions = await refresh_wallet_positions(db, WALLET, rpc_by_chain={8453: mock})
    assert len(positions) == 2

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

    # No RPC provided for chain 1 — must skip silently, not raise.
    positions = await refresh_wallet_positions(db, WALLET, rpc_by_chain={})
    assert positions == []
