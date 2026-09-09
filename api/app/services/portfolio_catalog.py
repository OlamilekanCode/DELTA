"""Database-backed portfolio contract catalogue sync.

Populates `portfolio_asset_contracts` from four sources, each independent
so a failure in one never touches rows already written by another or by a
previous successful sync:

1. CoinGecko `/coins/list?include_platform=true` (one call) — matched only
   against our own already-tracked crypto assets, resolving Ethereum/Base
   contract addresses. CoinGecko's list endpoint has no per-platform
   decimals field, so `decimals` here is an assumed default rather than a
   confirmed value — these rows are written verified=False until a human
   confirms the real decimals against a block explorer (see
   PortfolioContract's docstring; trusting a guessed decimals value would
   risk misvaluing a holding by orders of magnitude).
2. A curated set of wrapped-token aliases (WETH -> ETH, WBTC/cbBTC -> BTC)
   — not sourced from a live provider response, so these default to
   verified=False and require a human to confirm the address against a
   block explorer before the batch wallet reader will use them.
3. Robinhood's stock-token asset registry, filtered to our tracked stock
   symbols and to active Robinhood Chain (4663) deployments. The registry's
   response schema is explicitly best-effort/unconfirmed (see
   providers/robinhood.py's module docstring), so these rows are also
   written verified=False.
4. The chain's own native gas token (ETH on Ethereum/Base) — not fetched
   from any provider; 18 decimals is an EVM protocol constant rather than
   guessed data, so these rows are written verified=True directly.

Every row's identity is (chain_id, contract_address) — a token symbol alone
is never trusted to resolve a contract (see PortfolioContract's docstring).

Reconciliation: each provider-backed sync (1-3) tracks which
(chain_id, contract_address) keys it wrote this run and deactivates any
previously-synced row from that same source that wasn't touched — a
contract removed or delisted upstream must stop being read, not remain
active indefinitely just because upsert-only sync never revisits it.
Deactivation never deletes the row (cached wallet positions keep their
asset mapping for history), and never touches rows from a different
source.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio_contract import PortfolioContract
from app.providers.coingecko import CoinGeckoProvider
from app.providers.robinhood import RobinhoodAssetProvider
from app.services.portfolio_assets import NATIVE

log = logging.getLogger(__name__)

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ROBINHOOD_CHAIN_ID = 4663

_EVM_PLATFORM_TO_CHAIN_ID = {"ethereum": ETHEREUM_CHAIN_ID, "base": BASE_CHAIN_ID}
_NATIVE_ETH_CHAINS = (ETHEREUM_CHAIN_ID, BASE_CHAIN_ID)  # native gas token there is ETH

_DEFAULT_ERC20_DECIMALS = 18  # CoinGecko's coins/list has no per-platform decimals field
_NATIVE_GAS_TOKEN_DECIMALS = 18  # EVM protocol constant, not app-specific guessed data


@dataclass(frozen=True)
class CuratedAlias:
    chain_id: int
    contract_address: str
    decimals: int
    canonical_symbol: str  # must match an existing Asset.symbol


# Best-known public canonical addresses for major wrapped tokens. NOT sourced
# from a live provider response — each entry defaults to verified=False in
# the database and must be independently reconfirmed against a block
# explorer (Etherscan/Basescan) before a human flips it to verified=True.
# Never used by the wallet reader until that happens.
CURATED_ALIASES: list[CuratedAlias] = [
    CuratedAlias(ETHEREUM_CHAIN_ID, "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", 18, "ETH"),  # WETH (mainnet)
    CuratedAlias(ETHEREUM_CHAIN_ID, "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", 8, "BTC"),   # WBTC (mainnet)
    CuratedAlias(BASE_CHAIN_ID, "0x4200000000000000000000000000000000000006", 18, "ETH"),      # WETH (Base predeploy)
    CuratedAlias(BASE_CHAIN_ID, "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf", 8, "BTC"),         # cbBTC (Base)
    # Stablecoins — same "confirmed by a human, never trusted from memory
    # alone" treatment. USDG in particular (Global Dollar, a newer 2024
    # token) has the lowest confidence of any address here.
    CuratedAlias(ETHEREUM_CHAIN_ID, "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6, "USDC"),  # USDC (mainnet)
    CuratedAlias(ETHEREUM_CHAIN_ID, "0xdac17f958d2ee523a2206206994597c13d831ec7", 6, "USDT"),  # USDT (mainnet)
    CuratedAlias(BASE_CHAIN_ID, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", 6, "USDC"),        # USDC (Base)
]


async def _asset_by_symbol_map(db: AsyncSession, asset_types: str | list[str]) -> dict[str, Asset]:
    types = [asset_types] if isinstance(asset_types, str) else asset_types
    result = await db.execute(select(Asset).where(Asset.asset_type.in_(types)))
    return {a.symbol.upper(): a for a in result.scalars().all()}


async def _asset_by_coingecko_id_map(db: AsyncSession) -> dict[str, Asset]:
    result = await db.execute(
        select(Asset).where(Asset.asset_type == "crypto", Asset.coingecko_id.is_not(None))
    )
    return {a.coingecko_id: a for a in result.scalars().all() if a.coingecko_id}


async def _upsert_contract(
    db: AsyncSession,
    *,
    asset_id: int,
    chain_id: int,
    contract_address: str,
    contract_type: str,
    decimals: int,
    source: str,
    verified: bool,
    active: bool = True,
    current_multiplier: float | None = None,
) -> bool:
    """Insert or update one row, matched on (chain_id, contract_address) —
    never on symbol. Returns True if a row was written, False if a
    human-verified row's asset assignment was protected from being silently
    reassigned (see below) — the caller's count should not treat that as a
    normal successful match."""
    contract_address = contract_address.lower()
    existing_result = await db.execute(
        select(PortfolioContract).where(
            PortfolioContract.chain_id == chain_id,
            PortfolioContract.contract_address == contract_address,
        )
    )
    existing = existing_result.scalar_one_or_none()
    now = datetime.now(UTC)
    if existing is not None:
        if existing.verified and existing.asset_id != asset_id:
            # A verified contract address being resolved to a DIFFERENT
            # asset than before (an upstream data change, e.g. CoinGecko
            # remapping a platform address) must never be silently
            # reassigned — cached wallet positions already keyed to the old
            # asset would then be misvalued as the new one. Requires a
            # human to investigate and, if legitimate, explicitly
            # unverify/reassign the row first.
            log.warning(
                "Refusing to reassign verified contract %s on chain %s from asset_id=%s to asset_id=%s",
                contract_address, chain_id, existing.asset_id, asset_id,
            )
            return False
        if existing.verified and not verified:
            # A human already confirmed this row's asset/decimals/type/
            # source (and, for stock tokens, multiplier) against a block
            # explorer. A LATER sync pass that itself can't confirm those
            # values (verified=False — e.g. CoinGecko's guessed decimals,
            # or Robinhood's best-effort schema) must never silently
            # overwrite them: decimals=6 confirmed today must not become
            # decimals=18 tomorrow just because CoinGecko re-resolved the
            # same address. Only `active` (still-present-upstream tracking)
            # is safe to keep syncing here.
            existing.active = active
            existing.updated_at = now
            return True
        existing.asset_id = asset_id
        existing.contract_type = contract_type
        existing.decimals = decimals
        existing.source = source
        # Never downgrade an already-verified row just because a later sync
        # pass re-resolved it — verification is a one-way, human-confirmed
        # upgrade, not something a routine sync should silently revoke.
        existing.verified = existing.verified or verified
        existing.active = active
        existing.current_multiplier = current_multiplier
        existing.updated_at = now
    else:
        db.add(PortfolioContract(
            asset_id=asset_id, chain_id=chain_id, contract_address=contract_address,
            contract_type=contract_type, decimals=decimals, source=source,
            verified=verified, active=active, current_multiplier=current_multiplier,
            created_at=now, updated_at=now,
        ))
    return True


async def _reconcile(db: AsyncSession, source: str, touched_keys: set[tuple[int, str]]) -> int:
    """Guards _deactivate_stale_rows against an empty touched set — a
    provider response that's technically valid (a real list) but contains
    zero matched entries (network hiccup returning a near-empty page, an
    API change silently dropping fields our own parsing then filters out,
    etc.) must never be trusted as "confirmed: everything from this source
    is gone now". Only reconciles when there's at least one touched
    address as positive evidence this run actually saw real data."""
    if not touched_keys:
        log.warning(
            "%s sync touched zero contracts this run — skipping reconciliation "
            "rather than risk deactivating the entire source on a suspiciously empty response",
            source,
        )
        return 0
    return await _deactivate_stale_rows(db, source, touched_keys)


async def _deactivate_stale_rows(db: AsyncSession, source: str, touched_keys: set[tuple[int, str]]) -> int:
    """After a sync pass, deactivate any previously-synced row from this
    same `source` whose (chain_id, contract_address) wasn't touched this
    run — it's no longer present in the upstream data (removed, delisted,
    or renamed) and must stop being read by the wallet reader. Soft
    deactivation only: the row and its asset mapping are preserved for any
    cached wallet position history that still references it (see
    services/portfolio.py's _classify_positions, which excludes inactive
    contracts from valuation)."""
    result = await db.execute(
        select(PortfolioContract).where(PortfolioContract.source == source, PortfolioContract.active.is_(True))
    )
    deactivated = 0
    for row in result.scalars().all():
        if (row.chain_id, row.contract_address.lower()) not in touched_keys:
            row.active = False
            row.updated_at = datetime.now(UTC)
            deactivated += 1
    return deactivated


async def sync_crypto_contracts_from_coingecko(db: AsyncSession, cg: CoinGeckoProvider) -> dict:
    """Fetch the full CoinGecko coins/platforms list ONCE and match only our
    existing tracked crypto CoinGecko IDs — never used to discover new
    assets. Preserves previously-synced rows if this call fails."""
    counts = {"requested": 0, "matched": 0, "contracts_written": 0, "deactivated": 0, "failed": False}
    by_coingecko_id = await _asset_by_coingecko_id_map(db)
    counts["requested"] = len(by_coingecko_id)
    if not by_coingecko_id:
        return counts

    try:
        coins = await cg.fetch_coins_list_with_platforms()
    except Exception:
        log.exception("CoinGecko coins/list fetch failed — previous portfolio catalogue rows preserved")
        counts["failed"] = True
        return counts

    touched: set[tuple[int, str]] = set()
    for coin in coins:
        coingecko_id = coin.get("id")
        if not coingecko_id or coingecko_id not in by_coingecko_id:
            continue
        platforms = coin.get("platforms") or {}
        asset = by_coingecko_id[coingecko_id]
        matched_this_coin = False
        for platform_key, chain_id in _EVM_PLATFORM_TO_CHAIN_ID.items():
            address = platforms.get(platform_key)
            if not address or not isinstance(address, str) or not address.startswith("0x"):
                continue
            written = await _upsert_contract(
                db, asset_id=asset.id, chain_id=chain_id, contract_address=address,
                contract_type="erc20", decimals=_DEFAULT_ERC20_DECIMALS,
                # Decimals here is an assumed default, not a confirmed value
                # (CoinGecko's list endpoint has no per-platform decimals
                # field) — never auto-verified. See PortfolioContract's
                # docstring.
                source="coingecko", verified=False,
            )
            # Marked touched regardless of whether the write actually
            # happened — the address WAS present in this run's upstream
            # data, so it must never be deactivated by reconciliation just
            # because _upsert_contract refused to touch a protected
            # verified/reassignment-conflict row (see _upsert_contract).
            touched.add((chain_id, address.lower()))
            if written:
                counts["contracts_written"] += 1
            matched_this_coin = True
        if matched_this_coin:
            counts["matched"] += 1

    counts["deactivated"] = await _reconcile(db, "coingecko", touched)
    await db.commit()
    return counts


async def sync_curated_aliases(db: AsyncSession) -> dict:
    """Seed the curated wrapped-token and stablecoin aliases. Idempotent —
    re-running never duplicates rows or downgrades an already-verified one."""
    counts = {"requested": len(CURATED_ALIASES), "matched": 0, "contracts_written": 0}
    by_symbol = await _asset_by_symbol_map(db, ["crypto", "stablecoin"])
    for alias in CURATED_ALIASES:
        asset = by_symbol.get(alias.canonical_symbol.upper())
        if asset is None:
            continue
        written = await _upsert_contract(
            db, asset_id=asset.id, chain_id=alias.chain_id, contract_address=alias.contract_address,
            contract_type="erc20", decimals=alias.decimals, source="curated_alias", verified=False,
        )
        counts["matched"] += 1
        if written:
            counts["contracts_written"] += 1
    await db.commit()
    return counts


async def sync_robinhood_stock_tokens(db: AsyncSession, rh: RobinhoodAssetProvider) -> dict:
    """Fetch Robinhood's asset registry and store only active chain-4663
    deployments for our tracked stock symbols. Preserves previously-synced
    rows if this call fails."""
    counts = {"requested": 0, "matched": 0, "contracts_written": 0, "deactivated": 0, "failed": False}
    by_symbol = await _asset_by_symbol_map(db, "stock")
    counts["requested"] = len(by_symbol)
    if not by_symbol:
        return counts

    try:
        tokens = await rh.fetch_stock_tokens()
    except Exception:
        log.exception("Robinhood asset registry fetch failed — previous portfolio catalogue rows preserved")
        counts["failed"] = True
        return counts

    touched: set[tuple[int, str]] = set()
    for token in tokens:
        if token.chain_id != ROBINHOOD_CHAIN_ID or not token.active:
            continue
        asset = by_symbol.get(token.symbol)
        if asset is None:
            continue
        written = await _upsert_contract(
            db, asset_id=asset.id, chain_id=token.chain_id, contract_address=token.contract_address,
            contract_type="robinhood_stock", decimals=token.decimals,
            # The registry's response schema is explicitly best-effort and
            # not reconfirmed against a live response (see
            # providers/robinhood.py) — never auto-verified.
            source="robinhood", verified=False, active=token.active,
            current_multiplier=token.current_multiplier,
        )
        # Touched regardless of write outcome — see the matching comment
        # in sync_crypto_contracts_from_coingecko above.
        touched.add((token.chain_id, token.contract_address.lower()))
        counts["matched"] += 1
        if written:
            counts["contracts_written"] += 1

    counts["deactivated"] = await _reconcile(db, "robinhood", touched)
    await db.commit()
    return counts


async def sync_native_gas_tokens(db: AsyncSession) -> dict:
    """Register the chain's own native gas token (ETH on Ethereum/Base) as
    a portfolio contract. Not sourced from any provider response — there is
    nothing to fetch or guess: EVM native-token decimals are always 18, a
    protocol constant, so these rows are written verified=True directly."""
    counts = {"requested": 0, "matched": 0, "contracts_written": 0}
    by_symbol = await _asset_by_symbol_map(db, "crypto")
    eth_asset = by_symbol.get("ETH")
    counts["requested"] = len(_NATIVE_ETH_CHAINS)
    if eth_asset is None:
        return counts

    for chain_id in _NATIVE_ETH_CHAINS:
        written = await _upsert_contract(
            db, asset_id=eth_asset.id, chain_id=chain_id, contract_address=NATIVE,
            contract_type="native", decimals=_NATIVE_GAS_TOKEN_DECIMALS,
            source="native", verified=True,
        )
        if written:
            counts["matched"] += 1
            counts["contracts_written"] += 1

    await db.commit()
    return counts


async def get_verified_contracts_for_chain(db: AsyncSession, chain_id: int) -> list[PortfolioContract]:
    """Only verified, active rows are ever handed to the wallet reader —
    a curated alias sitting at verified=False is invisible here until a
    human confirms it."""
    result = await db.execute(
        select(PortfolioContract).where(
            PortfolioContract.chain_id == chain_id,
            PortfolioContract.verified.is_(True),
            PortfolioContract.active.is_(True),
        )
    )
    return list(result.scalars().all())


async def sync_portfolio_catalogue(
    db: AsyncSession, cg: CoinGeckoProvider, rh: RobinhoodAssetProvider
) -> dict:
    """Run all four catalogue sources. Each is independent — one failing
    never rolls back or blocks the others, and never deletes previously
    verified rows (upsert-only, deactivate-on-removal — see
    _deactivate_stale_rows — not wipe-then-repopulate)."""
    crypto_counts = await sync_crypto_contracts_from_coingecko(db, cg)
    alias_counts = await sync_curated_aliases(db)
    robinhood_counts = await sync_robinhood_stock_tokens(db, rh)
    native_counts = await sync_native_gas_tokens(db)
    return {
        "crypto_coingecko": crypto_counts,
        "curated_aliases": alias_counts,
        "robinhood_stock": robinhood_counts,
        "native_gas_tokens": native_counts,
    }
