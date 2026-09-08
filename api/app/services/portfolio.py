"""Portfolio tier derivation and wallet exposure calculation.

Tier boundaries are exact and inclusive: $49.99 -> locked, $50.00 -> summary,
$250.00 -> detailed, $1,000.00 -> premium. Tier is set only by a verified
purchase claim (see services/purchase_verification.py) — it is never
recalculated here from current prices.

Portfolio *access* additionally requires the wallet's current $SynthEx
balance to clear the holder threshold (see services/holder.py) — a verified
tier is retained even if access is temporarily suspended by an insufficient
current balance, and access is restored automatically once the balance is
sufficient again, with no new purchase required.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.portfolio import WalletEntitlement
from app.models.quote import AssetQuote
from app.models.wallet_position import CachedWalletPosition
from app.services.blockchain import RpcProvider
from app.services.portfolio_assets import NATIVE, contracts_for_chain

TIER_THRESHOLDS = {
    "summary": 5_000,    # $50.00
    "detailed": 25_000,  # $250.00
    "premium": 100_000,  # $1,000.00
}


def get_tier(cumulative_usd_cents: int) -> str:
    if cumulative_usd_cents >= TIER_THRESHOLDS["premium"]:
        return "premium"
    if cumulative_usd_cents >= TIER_THRESHOLDS["detailed"]:
        return "detailed"
    if cumulative_usd_cents >= TIER_THRESHOLDS["summary"]:
        return "summary"
    return "locked"


async def get_entitlement(db: AsyncSession, wallet_address: str) -> WalletEntitlement | None:
    result = await db.execute(
        select(WalletEntitlement).where(WalletEntitlement.wallet_address == wallet_address.lower())
    )
    return result.scalar_one_or_none()


async def get_or_create_entitlement(db: AsyncSession, wallet_address: str) -> WalletEntitlement:
    entitlement = await get_entitlement(db, wallet_address)
    if entitlement is None:
        entitlement = WalletEntitlement(
            wallet_address=wallet_address.lower(),
            tier="locked",
            cumulative_usd_cents=0,
            updated_at=datetime.now(UTC),
        )
        db.add(entitlement)
        await db.commit()
    return entitlement


async def refresh_wallet_positions(
    db: AsyncSession, wallet_address: str, rpc_by_chain: dict[int, RpcProvider] | None = None
) -> list[CachedWalletPosition]:
    """Read on-chain balances for every configured portfolio asset contract
    and upsert `cached_wallet_positions`. Never called on ordinary portfolio
    page requests — only from explicit/background refresh. A chain with no
    RPC provider supplied, or no configured contracts, is silently skipped
    (not an error) — this is how Ethereum/Base stay disabled until enabled.
    """
    settings = get_settings()
    wallet_lower = wallet_address.lower()
    rpc_by_chain = rpc_by_chain or {}

    chain_ids = set(settings.parsed_portfolio_chain_ids)
    if settings.synthex_chain_id:
        chain_ids.add(settings.synthex_chain_id)

    now = datetime.now(UTC)
    updated: list[CachedWalletPosition] = []

    for chain_id in chain_ids:
        contracts = contracts_for_chain(chain_id)
        rpc = rpc_by_chain.get(chain_id)
        if not contracts or rpc is None:
            continue
        try:
            block_number = await rpc.get_block_number()
        except Exception:
            continue

        for contract in contracts:
            try:
                raw = (
                    await rpc.get_native_balance(wallet_lower)
                    if contract.contract_address == NATIVE
                    else await rpc.get_erc20_balance(contract.contract_address, wallet_lower)
                )
            except Exception:
                continue

            asset_result = await db.execute(select(Asset).where(Asset.symbol == contract.symbol))
            asset = asset_result.scalar_one_or_none()

            existing_result = await db.execute(
                select(CachedWalletPosition).where(
                    CachedWalletPosition.wallet_address == wallet_lower,
                    CachedWalletPosition.chain_id == chain_id,
                    CachedWalletPosition.contract_address == contract.contract_address,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is not None:
                existing.quantity_raw = str(raw)
                existing.decimals = contract.decimals
                existing.asset_id = asset.id if asset else None
                existing.block_number = block_number
                existing.updated_at = now
                updated.append(existing)
            else:
                row = CachedWalletPosition(
                    wallet_address=wallet_lower,
                    chain_id=chain_id,
                    contract_address=contract.contract_address,
                    asset_id=asset.id if asset else None,
                    quantity_raw=str(raw),
                    decimals=contract.decimals,
                    block_number=block_number,
                    updated_at=now,
                )
                db.add(row)
                updated.append(row)

    await db.commit()
    return updated


async def _stock_exposure_for_weights(
    db: AsyncSession, stock: Asset, weights: list[tuple[Asset, Decimal]], excluded: list[dict]
) -> tuple[float, list[dict], list[dict]]:
    scores_result = await db.execute(
        select(StoredExposureScore).where(StoredExposureScore.stock_id == stock.id)
    )
    score_by_crypto = {s.crypto_id: s.score for s in scores_result.scalars().all()}

    total = Decimal(0)
    contributing: list[dict] = []
    stock_excluded = list(excluded)
    for asset, weight in weights:
        score = score_by_crypto.get(asset.id)
        if score is None:
            stock_excluded.append({"symbol": asset.symbol, "reason": "no_exposure_score_for_stock"})
            continue
        total += weight * Decimal(str(score))
        contributing.append({"symbol": asset.symbol, "weight": float(weight), "score": score})
    return float(total), contributing, stock_excluded


async def compute_portfolio_exposure(
    db: AsyncSession, wallet_address: str, stock_symbol: str | None = None
) -> dict:
    """Σ(crypto portfolio weight × signed stock/crypto Exposure Score) for a
    selected stock, or a ranked summary across every stock with data.

    Reads only stored positions and stored quotes/scores — never a live
    provider call. Returns an honest empty/excluded structure (never a
    fabricated score) whenever positions, prices or scores are missing.
    """
    wallet_lower = wallet_address.lower()
    positions_result = await db.execute(
        select(CachedWalletPosition).where(CachedWalletPosition.wallet_address == wallet_lower)
    )
    positions = positions_result.scalars().all()

    if not positions:
        return {
            "portfolio_exposure_score": None,
            "assets": [],
            "excluded": [],
            "data_ts": None,
            "note": "No wallet positions found yet — refresh to read current on-chain holdings",
        }

    excluded: list[dict] = []
    weights: list[tuple[Asset, Decimal]] = []
    total_usd = Decimal(0)
    valued: list[tuple[Asset, Decimal]] = []
    data_ts = max((p.updated_at for p in positions), default=None)

    for p in positions:
        if p.asset_id is None:
            excluded.append({"contract_address": p.contract_address, "reason": "unsupported_token"})
            continue
        asset = await db.get(Asset, p.asset_id)
        if asset is None:
            continue
        quote_result = await db.execute(select(AssetQuote).where(AssetQuote.asset_id == p.asset_id))
        quote_row = quote_result.scalar_one_or_none()
        if quote_row is None:
            excluded.append({"symbol": asset.symbol, "reason": "missing_price"})
            continue
        qty = Decimal(p.quantity_raw) / Decimal(10 ** p.decimals)
        usd_value = qty * Decimal(str(quote_row.price_usd))
        if usd_value <= 0:
            continue
        valued.append((asset, usd_value))
        total_usd += usd_value

    if total_usd <= 0:
        return {
            "portfolio_exposure_score": None,
            "assets": [],
            "excluded": excluded,
            "data_ts": data_ts.isoformat() if data_ts else None,
            "note": "No valued positions — every holding is unsupported or missing a stored price",
        }

    weights = [(asset, usd_value / total_usd) for asset, usd_value in valued]

    if stock_symbol:
        stock_result = await db.execute(
            select(Asset).where(Asset.symbol == stock_symbol.upper(), Asset.asset_type == "stock")
        )
        stock = stock_result.scalar_one_or_none()
        if stock is None:
            return {"error": "unknown_stock", "portfolio_exposure_score": None, "assets": []}
        score, contributing, stock_excluded = await _stock_exposure_for_weights(db, stock, weights, excluded)
        return {
            "stock": stock.symbol,
            "portfolio_exposure_score": round(score, 4),
            "assets": contributing,
            "excluded": stock_excluded,
            "data_ts": data_ts.isoformat() if data_ts else None,
        }

    stocks_result = await db.execute(select(Asset).where(Asset.asset_type == "stock").order_by(Asset.symbol))
    ranked: list[dict] = []
    for stock in stocks_result.scalars().all():
        score, contributing, _ = await _stock_exposure_for_weights(db, stock, weights, excluded)
        if contributing:
            ranked.append({"stock": stock.symbol, "portfolio_exposure_score": round(score, 4), "assets": contributing})
    ranked.sort(key=lambda r: abs(r["portfolio_exposure_score"]), reverse=True)

    return {
        "ranked": ranked,
        "assets": [{"symbol": asset.symbol, "weight": float(weight)} for asset, weight in weights],
        "excluded": excluded,
        "data_ts": data_ts.isoformat() if data_ts else None,
    }
