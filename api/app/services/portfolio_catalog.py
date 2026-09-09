"""Database-backed portfolio contract catalogue sync.

Populates `portfolio_asset_contracts` from three sources, each independent
so a failure in one never touches rows already written by another or by a
previous successful sync:

1. CoinGecko `/coins/list?include_platform=true` (one call) — matched only
   against our own already-tracked crypto assets, resolving verified
   Ethereum/Base contract addresses.
2. A curated set of wrapped-token aliases (WETH -> ETH, WBTC/cbBTC -> BTC)
   — not sourced from a live provider response, so these default to
   verified=False and require a human to confirm the address against a
   block explorer before the batch wallet reader will use them.
3. Robinhood's stock-token asset registry, filtered to our tracked stock
   symbols and to active Robinhood Chain (4663) deployments.

Every row's identity is (chain_id, contract_address) — a token symbol alone
is never trusted to resolve a contract (see PortfolioContract's docstring).
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

log = logging.getLogger(__name__)

ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ROBINHOOD_CHAIN_ID = 4663

_EVM_PLATFORM_TO_CHAIN_ID = {"ethereum": ETHEREUM_CHAIN_ID, "base": BASE_CHAIN_ID}

_DEFAULT_ERC20_DECIMALS = 18  # CoinGecko's coins/list has no per-platform decimals field


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
]


async def _asset_by_symbol_map(db: AsyncSession, asset_type: str) -> dict[str, Asset]:
    result = await db.execute(select(Asset).where(Asset.asset_type == asset_type))
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
) -> bool:
    """Insert or update one row, matched on (chain_id, contract_address) —
    never on symbol. Returns True if a row was written."""
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
        existing.asset_id = asset_id
        existing.contract_type = contract_type
        existing.decimals = decimals
        existing.source = source
        # Never downgrade an already-verified row just because a later sync
        # pass re-resolved it — verification is a one-way, human-confirmed
        # upgrade, not something a routine sync should silently revoke.
        existing.verified = existing.verified or verified
        existing.active = active
        existing.updated_at = now
    else:
        db.add(PortfolioContract(
            asset_id=asset_id, chain_id=chain_id, contract_address=contract_address,
            contract_type=contract_type, decimals=decimals, source=source,
            verified=verified, active=active, created_at=now, updated_at=now,
        ))
    return True


async def sync_crypto_contracts_from_coingecko(db: AsyncSession, cg: CoinGeckoProvider) -> dict:
    """Fetch the full CoinGecko coins/platforms list ONCE and match only our
    existing tracked crypto CoinGecko IDs — never used to discover new
    assets. Preserves previously-synced rows if this call fails."""
    counts = {"requested": 0, "matched": 0, "contracts_written": 0, "failed": False}
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
            await _upsert_contract(
                db, asset_id=asset.id, chain_id=chain_id, contract_address=address,
                contract_type="erc20", decimals=_DEFAULT_ERC20_DECIMALS,
                source="coingecko", verified=True,
            )
            counts["contracts_written"] += 1
            matched_this_coin = True
        if matched_this_coin:
            counts["matched"] += 1

    await db.commit()
    return counts


async def sync_curated_aliases(db: AsyncSession) -> dict:
    """Seed the curated wrapped-token aliases. Idempotent — re-running never
    duplicates rows or downgrades an already-verified one."""
    counts = {"requested": len(CURATED_ALIASES), "matched": 0, "contracts_written": 0}
    by_symbol = await _asset_by_symbol_map(db, "crypto")
    for alias in CURATED_ALIASES:
        asset = by_symbol.get(alias.canonical_symbol.upper())
        if asset is None:
            continue
        await _upsert_contract(
            db, asset_id=asset.id, chain_id=alias.chain_id, contract_address=alias.contract_address,
            contract_type="erc20", decimals=alias.decimals, source="curated_alias", verified=False,
        )
        counts["matched"] += 1
        counts["contracts_written"] += 1
    await db.commit()
    return counts


async def sync_robinhood_stock_tokens(db: AsyncSession, rh: RobinhoodAssetProvider) -> dict:
    """Fetch Robinhood's asset registry and store only active chain-4663
    deployments for our tracked stock symbols. Preserves previously-synced
    rows if this call fails."""
    counts = {"requested": 0, "matched": 0, "contracts_written": 0, "failed": False}
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

    for token in tokens:
        if token.chain_id != ROBINHOOD_CHAIN_ID or not token.active:
            continue
        asset = by_symbol.get(token.symbol)
        if asset is None:
            continue
        await _upsert_contract(
            db, asset_id=asset.id, chain_id=token.chain_id, contract_address=token.contract_address,
            contract_type="robinhood_stock", decimals=token.decimals,
            source="robinhood", verified=True, active=token.active,
        )
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
    """Run all three catalogue sources. Each is independent — one failing
    never rolls back or blocks the others, and never deletes previously
    verified rows (upsert-only, no wipe-then-repopulate)."""
    crypto_counts = await sync_crypto_contracts_from_coingecko(db, cg)
    alias_counts = await sync_curated_aliases(db)
    robinhood_counts = await sync_robinhood_stock_tokens(db, rh)
    return {
        "crypto_coingecko": crypto_counts,
        "curated_aliases": alias_counts,
        "robinhood_stock": robinhood_counts,
    }
