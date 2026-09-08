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

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.portfolio import WalletEntitlement
from app.models.quote import AssetQuote
from app.models.wallet_position import CachedWalletPosition
from app.services.blockchain import JsonRpcProvider, RpcProvider
from app.services.portfolio_assets import NATIVE, contracts_for_chain

TIER_THRESHOLDS = {
    "summary": 5_000,    # $50.00
    "detailed": 25_000,  # $250.00
    "premium": 100_000,  # $1,000.00
}

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453

# Features that exist for the "detailed" tier but are not yet built — surfaced
# to "premium" wallets as explicitly coming_soon rather than silently absent.
PREMIUM_COMING_SOON_FEATURES = ["advanced_graphs", "longer_portfolio_history", "alerts"]


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


@dataclass
class PortfolioRefreshResult:
    """Structured outcome of a wallet-position refresh — always tells the
    caller *why* nothing happened rather than letting a silent no-op look
    like a successful zero-position refresh."""

    status: str  # "ok" | "not_configured"
    chains_attempted: int = 0
    contracts_attempted: int = 0
    positions_refreshed: int = 0
    skipped: int = 0
    failed: int = 0
    positions: list[CachedWalletPosition] = field(default_factory=list)
    message: str | None = None


def build_rpc_by_chain(settings: Settings) -> dict[int, RpcProvider]:
    """Real, server-only `JsonRpcProvider` instances from configured RPC URLs
    — never invents a chain ID, RPC URL or contract address. A chain with no
    URL configured simply has no provider entry, so its contracts are
    skipped rather than queried against the wrong network."""
    mapping: dict[int, RpcProvider] = {}
    if settings.synthex_chain_id and settings.robinhood_rpc_url:
        mapping[settings.synthex_chain_id] = JsonRpcProvider(settings.robinhood_rpc_url)
    if settings.ethereum_rpc_url:
        mapping[ETHEREUM_CHAIN_ID] = JsonRpcProvider(settings.ethereum_rpc_url)
    if settings.base_rpc_url:
        mapping[BASE_CHAIN_ID] = JsonRpcProvider(settings.base_rpc_url)
    return mapping


async def refresh_wallet_positions(
    db: AsyncSession, wallet_address: str, rpc_by_chain: dict[int, RpcProvider] | None = None
) -> PortfolioRefreshResult:
    """Read on-chain balances for every configured portfolio asset contract
    and upsert `cached_wallet_positions`. Never called on ordinary portfolio
    page requests — only from explicit/background refresh.

    `rpc_by_chain` is `None` in production: real providers are built from
    server-only config (`ROBINHOOD_RPC_URL`, `ETHEREUM_RPC_URL`,
    `BASE_RPC_URL`) via `build_rpc_by_chain`. Tests inject a dict of mock
    providers directly — including an explicit `{}` to simulate a chain with
    contracts configured but no RPC reachable for it.

    A chain whose RPC reports back a different `chain_id` than expected is
    treated as failed (never trusted) rather than silently using the wrong
    network's balances. An RPC or DB failure for one contract/chain never
    touches previously cached positions for others.
    """
    settings = get_settings()
    wallet_lower = wallet_address.lower()

    if rpc_by_chain is None:
        rpc_by_chain = build_rpc_by_chain(settings)

    chain_ids = set(settings.parsed_portfolio_chain_ids)
    if settings.synthex_chain_id:
        chain_ids.add(settings.synthex_chain_id)

    contracts_by_chain = {cid: contracts for cid in chain_ids if (contracts := contracts_for_chain(cid))}
    total_contracts = sum(len(c) for c in contracts_by_chain.values())

    if total_contracts == 0 or not rpc_by_chain:
        return PortfolioRefreshResult(
            status="not_configured",
            message="No portfolio contract catalogue or RPC provider is configured yet",
        )

    now = datetime.now(UTC)
    result = PortfolioRefreshResult(status="ok", chains_attempted=len(contracts_by_chain))

    for chain_id, contracts in contracts_by_chain.items():
        result.contracts_attempted += len(contracts)
        rpc = rpc_by_chain.get(chain_id)
        if rpc is None:
            result.skipped += len(contracts)
            continue

        try:
            reported_chain_id = await rpc.get_chain_id()
            if reported_chain_id != chain_id:
                result.failed += len(contracts)
                continue
            block_number = await rpc.get_block_number()
        except Exception:
            result.failed += len(contracts)
            continue

        for contract in contracts:
            try:
                raw = (
                    await rpc.get_native_balance(wallet_lower)
                    if contract.contract_address == NATIVE
                    else await rpc.get_erc20_balance(contract.contract_address, wallet_lower)
                )
            except Exception:
                result.failed += 1
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
                result.positions.append(existing)
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
                result.positions.append(row)
            result.positions_refreshed += 1

    await db.commit()
    return result


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

    category_totals: dict[str, Decimal] = {}
    for asset, weight in weights:
        category_totals[asset.category] = category_totals.get(asset.category, Decimal(0)) + weight
    category_exposure = sorted(
        ({"category": c, "weight": float(w)} for c, w in category_totals.items()),
        key=lambda row: row["weight"],
        reverse=True,
    )

    return {
        "ranked": ranked,
        "assets": [{"symbol": asset.symbol, "weight": float(weight)} for asset, weight in weights],
        "category_exposure": category_exposure,
        "excluded": excluded,
        "data_ts": data_ts.isoformat() if data_ts else None,
    }


def shape_portfolio_response(tier: str, exposure: dict) -> dict:
    """Trim the fully-computed exposure payload to what each tier is allowed
    to see. Enforced server-side — the frontend must never be the only thing
    hiding summary-tier detail.

    - "summary": headline score and coverage count only — no individual
      holdings, weights, excluded assets or per-stock contribution data.
    - "detailed": the full payload as computed (weights, excluded, category
      aggregation, ranked stock exposure).
    - "premium": the full "detailed" payload plus a `coming_soon` list for
      features that exist in the UI but aren't built yet.
    """
    if "error" in exposure:
        return exposure

    if tier == "summary":
        return _summary_shape(exposure)

    if tier == "premium":
        return {**exposure, "coming_soon": PREMIUM_COMING_SOON_FEATURES}

    return exposure


def _summary_shape(exposure: dict) -> dict:
    ranked = exposure.get("ranked")
    if ranked is not None:
        scores = [r["portfolio_exposure_score"] for r in ranked]
        shaped = {
            "portfolio_exposure_score": round(sum(scores) / len(scores), 4) if scores else None,
            "stocks_covered": len(ranked),
            "data_ts": exposure.get("data_ts"),
        }
    else:
        score = exposure.get("portfolio_exposure_score")
        shaped = {
            "portfolio_exposure_score": score,
            "stocks_covered": 1 if score is not None else 0,
            "data_ts": exposure.get("data_ts"),
        }
    if exposure.get("note"):
        shaped["note"] = exposure["note"]
    return shaped
