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
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.asset import Asset
from app.models.exposure_score import StoredExposureScore
from app.models.portfolio import WalletEntitlement
from app.models.portfolio_contract import PortfolioContract
from app.models.quote import AssetQuote
from app.models.wallet_position import CachedWalletPosition
from app.services.blockchain import JsonRpcProvider, RpcProvider
from app.services.portfolio_catalog import get_verified_contracts_for_chain
from app.services.wallet_reader import read_balances_batched

# On-chain positions are refreshed only on explicit user action (never on an
# ordinary page view — see refresh_wallet_positions), so a flat threshold is
# used rather than a market-hours-aware one: there is no "market open" for a
# wallet balance snapshot.
POSITIONS_STALE_AFTER = timedelta(minutes=30)
QUOTES_STALE_AFTER = timedelta(minutes=45)

# An authenticated user can call POST /portfolio/refresh repeatedly, and
# unlike the single holder-balance check, one refresh here can fan out into
# many RPC calls (every configured chain x contract). Floor how often it
# actually hits the RPC, same principle as holder.REFRESH_MIN_INTERVAL.
PORTFOLIO_REFRESH_MIN_INTERVAL = timedelta(seconds=30)

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
    """Standalone convenience — commits immediately if a new entitlement row
    had to be created. Never call this from inside a larger transaction
    (e.g. purchase verification) that must commit atomically as a whole —
    use `get_or_create_entitlement_in_transaction` there instead."""
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


async def get_or_create_entitlement_in_transaction(db: AsyncSession, wallet_address: str) -> WalletEntitlement:
    """Transaction-safe variant for callers that make further changes and
    must commit everything atomically themselves (e.g. purchase
    verification writing a claim + entitlement update in one transaction).
    Uses `flush()`, never `commit()` — a new entitlement row is visible to
    the rest of the same transaction but only persists once the caller's
    own commit succeeds, so a failure anywhere in that transaction rolls
    the new entitlement back along with everything else."""
    entitlement = await get_entitlement(db, wallet_address)
    if entitlement is None:
        entitlement = WalletEntitlement(
            wallet_address=wallet_address.lower(),
            tier="locked",
            cumulative_usd_cents=0,
            updated_at=datetime.now(UTC),
        )
        db.add(entitlement)
        await db.flush()
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
    """Read on-chain balances for every verified portfolio asset contract
    (see services/portfolio_catalog.get_verified_contracts_for_chain) and
    upsert `cached_wallet_positions`. Never called on ordinary portfolio
    page requests — only from explicit/background refresh, and floored to
    once per PORTFOLIO_REFRESH_MIN_INTERVAL per wallet.

    ERC-20 balances are read a handful of RPC calls per chain via
    Multicall3 (see services/wallet_reader.py), not one call per token —
    the native gas-token balance is always its own single direct call.

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

    contracts_by_chain: dict[int, list[PortfolioContract]] = {}
    for cid in chain_ids:
        contracts = await get_verified_contracts_for_chain(db, cid)
        if contracts:
            contracts_by_chain[cid] = contracts
    total_contracts = sum(len(c) for c in contracts_by_chain.values())

    if total_contracts == 0 or not rpc_by_chain:
        return PortfolioRefreshResult(
            status="not_configured",
            message="No portfolio contract catalogue or RPC provider is configured yet",
        )

    now = datetime.now(UTC)

    # A refresh here can fan out into many RPC calls (every configured
    # chain x contract) — floor how often an authenticated user can trigger
    # that fan-out by serving the still-fresh cached rows instead.
    last_refresh_result = await db.execute(
        select(func.max(CachedWalletPosition.updated_at)).where(
            CachedWalletPosition.wallet_address == wallet_lower
        )
    )
    last_refresh = last_refresh_result.scalar_one_or_none()
    if last_refresh is not None:
        last_refresh_aware = last_refresh if last_refresh.tzinfo is not None else last_refresh.replace(tzinfo=UTC)
        if now - last_refresh_aware < PORTFOLIO_REFRESH_MIN_INTERVAL:
            cached_result = await db.execute(
                select(CachedWalletPosition).where(CachedWalletPosition.wallet_address == wallet_lower)
            )
            return PortfolioRefreshResult(
                status="ok",
                positions=list(cached_result.scalars().all()),
                message="Using cached positions — refreshed within the last 30 seconds",
            )

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

        # A handful of RPC requests for this whole chain (native balance +
        # chunked Multicall3 batches), never one request per token.
        multicall_override = settings.parsed_multicall3_address_overrides.get(chain_id)
        balances = await read_balances_batched(rpc, chain_id, wallet_lower, contracts, multicall_override)

        for contract in contracts:
            if contract.contract_address not in balances:
                # Missing means that specific contract's read failed
                # (allowFailure in the batch, or the fallback per-token call
                # raised) — never treated as a confirmed zero, and the
                # existing cached row for it is left untouched.
                result.failed += 1
                continue
            raw = balances[contract.contract_address]

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
                existing.asset_id = contract.asset_id
                existing.block_number = block_number
                existing.updated_at = now
                result.positions.append(existing)
            else:
                row = CachedWalletPosition(
                    wallet_address=wallet_lower,
                    chain_id=chain_id,
                    contract_address=contract.contract_address,
                    asset_id=contract.asset_id,
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
            "positions_stale": True,
            "note": "No wallet positions found yet — refresh to read current on-chain holdings",
        }

    excluded: list[dict] = []
    weights: list[tuple[Asset, Decimal]] = []
    total_usd = Decimal(0)
    valued: list[tuple[Asset, Decimal]] = []
    # The portfolio-level snapshot is only as fresh as its stalest
    # constituent position — using the newest position's timestamp would
    # let one freshly-refreshed holding mask every other position being
    # long out of date, so both the displayed data_ts and the staleness
    # check use the OLDEST position timestamp (same convention as
    # oldest_quote_ts below).
    data_ts = min((p.updated_at for p in positions), default=None)
    data_ts_aware = data_ts if (data_ts is None or data_ts.tzinfo is not None) else data_ts.replace(tzinfo=UTC)
    positions_stale = data_ts_aware is None or (datetime.now(UTC) - data_ts_aware) > POSITIONS_STALE_AFTER

    oldest_quote_ts: datetime | None = None
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
        quote_ts = quote_row.ts if quote_row.ts.tzinfo is not None else quote_row.ts.replace(tzinfo=UTC)
        oldest_quote_ts = quote_ts if oldest_quote_ts is None else min(oldest_quote_ts, quote_ts)
        valued.append((asset, usd_value))
        total_usd += usd_value

    quotes_stale = oldest_quote_ts is None or (datetime.now(UTC) - oldest_quote_ts) > QUOTES_STALE_AFTER

    if total_usd <= 0:
        return {
            "portfolio_exposure_score": None,
            "assets": [],
            "excluded": excluded,
            "data_ts": data_ts.isoformat() if data_ts else None,
            "positions_stale": positions_stale,
            "total_usd_value": 0.0,
            "note": "No valued positions — every holding is unsupported or missing a stored price",
        }

    weights = [(asset, usd_value / total_usd) for asset, usd_value in valued]
    # Coverage: how much of the wallet's SUPPORTED, valued holdings this
    # analysis actually represents — a result built from one small holding
    # must never be presented as if it spoke for the whole wallet.
    coverage = {
        "total_usd_value": float(total_usd),
        "supported_position_count": len(valued),
        "excluded_position_count": len(excluded),
        "positions_stale": positions_stale,
        "quotes_stale": quotes_stale,
    }

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
            **coverage,
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
        **coverage,
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
    # Freshness/coverage counts are safe to surface at every tier — they are
    # not detailed financial data (no per-asset weights or symbols), just a
    # signal that the user should refresh and how much of the wallet this
    # covers. Dropping supported_position_count here (while keeping
    # total_usd_value) left the frontend showing "0 supported positions"
    # alongside a real, non-zero dollar total.
    for key in ("positions_stale", "quotes_stale", "total_usd_value", "supported_position_count", "excluded_position_count"):
        if key in exposure:
            shaped[key] = exposure[key]
    return shaped
