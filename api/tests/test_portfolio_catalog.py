"""Portfolio contract catalogue sync: CoinGecko-matched crypto contracts,
curated wrapped-token aliases, and Robinhood stock-token registry sync.

Identity is always (chain_id, contract_address) — never a token symbol
alone — and a failed fetch from any one source must never touch rows
already written (by that source or any other).
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio_contract import PortfolioContract
from app.services.portfolio_assets import NATIVE
from app.services.portfolio_catalog import (
    BASE_CHAIN_ID,
    ETHEREUM_CHAIN_ID,
    ROBINHOOD_CHAIN_ID,
    sync_crypto_contracts_from_coingecko,
    sync_curated_aliases,
    sync_native_gas_tokens,
    sync_robinhood_stock_tokens,
)


class _FakeCoinGecko:
    def __init__(self, coins: list[dict] | None = None, raise_error: bool = False) -> None:
        self._coins = coins or []
        self._raise = raise_error

    async def fetch_coins_list_with_platforms(self) -> list[dict]:
        if self._raise:
            raise RuntimeError("coingecko down")
        return self._coins


class _FakeRobinhood:
    def __init__(self, items: list[dict] | None = None, raise_error: bool = False) -> None:
        self._items = items or []
        self._raise = raise_error

    async def fetch_stock_tokens(self):
        from app.providers.robinhood import RobinhoodStockToken

        if self._raise:
            raise RuntimeError("robinhood down")
        tokens = []
        for item in self._items:
            tokens.append(RobinhoodStockToken(
                symbol=item["symbol"], chain_id=item["chain_id"],
                contract_address=item["contract_address"], decimals=item.get("decimals", 18),
                active=item.get("active", True), current_multiplier=item.get("current_multiplier"),
            ))
        return tokens


async def _contracts(db: AsyncSession) -> list[PortfolioContract]:
    result = await db.execute(select(PortfolioContract))
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_sync_crypto_contracts_matches_only_tracked_coingecko_ids(db: AsyncSession) -> None:
    btc = (await db.execute(select(Asset).where(Asset.symbol == "BTC"))).scalar_one()

    cg = _FakeCoinGecko(coins=[
        {"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xWBTCFAKE", "solana": "irrelevant"}},
        {"id": "some-untracked-coin", "symbol": "xyz", "platforms": {"ethereum": "0xShouldNeverAppear"}},
    ])
    counts = await sync_crypto_contracts_from_coingecko(db, cg)

    assert counts["failed"] is False
    assert counts["matched"] == 1

    rows = await _contracts(db)
    addresses = {r.contract_address for r in rows}
    assert "0xwbtcfake" in addresses
    assert "0xshouldneverappear" not in addresses
    btc_row = next(r for r in rows if r.contract_address == "0xwbtcfake")
    assert btc_row.asset_id == btc.id
    assert btc_row.chain_id == ETHEREUM_CHAIN_ID
    # CoinGecko's list endpoint has no per-platform decimals field — the
    # decimals stored here is an assumed default, never confirmed, so this
    # must never be auto-verified (would risk misvaluing a holding by
    # orders of magnitude if the real decimals differ).
    assert btc_row.verified is False
    assert btc_row.source == "coingecko"


@pytest.mark.asyncio
async def test_sync_crypto_contracts_stores_ethereum_and_base_only(db: AsyncSession) -> None:
    cg = _FakeCoinGecko(coins=[
        {
            "id": "ethereum", "symbol": "eth",
            "platforms": {"ethereum": "0xEthMainnet", "base": "0xEthOnBase", "polygon-pos": "0xNotStored"},
        },
    ])
    await sync_crypto_contracts_from_coingecko(db, cg)

    rows = await _contracts(db)
    chain_ids = {r.chain_id for r in rows}
    assert chain_ids == {ETHEREUM_CHAIN_ID, BASE_CHAIN_ID}
    assert not any(r.contract_address == "0xnotstored" for r in rows)


@pytest.mark.asyncio
async def test_sync_crypto_contracts_preserves_previous_rows_on_fetch_failure(db: AsyncSession) -> None:
    # First sync succeeds and writes a row.
    good_cg = _FakeCoinGecko(coins=[{"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xWBTCFAKE"}}])
    await sync_crypto_contracts_from_coingecko(db, good_cg)
    before = await _contracts(db)
    assert len(before) == 1

    # Second sync fails outright — the row from the first sync must survive untouched.
    failing_cg = _FakeCoinGecko(raise_error=True)
    counts = await sync_crypto_contracts_from_coingecko(db, failing_cg)
    assert counts["failed"] is True

    after = await _contracts(db)
    assert len(after) == 1
    assert after[0].contract_address == "0xwbtcfake"


@pytest.mark.asyncio
async def test_sync_curated_aliases_defaults_to_unverified(db: AsyncSession) -> None:
    counts = await sync_curated_aliases(db)
    assert counts["contracts_written"] > 0

    rows = await _contracts(db)
    assert rows  # WETH/WBTC/cbBTC aliases matched against ETH/BTC assets
    for row in rows:
        assert row.source == "curated_alias"
        # Never sourced from a live provider response — must never be
        # auto-verified, only a human confirming against a block explorer
        # can flip this.
        assert row.verified is False


@pytest.mark.asyncio
async def test_sync_curated_aliases_idempotent_no_duplicates(db: AsyncSession) -> None:
    await sync_curated_aliases(db)
    first_count = len(await _contracts(db))
    await sync_curated_aliases(db)
    second_count = len(await _contracts(db))
    assert first_count == second_count


@pytest.mark.asyncio
async def test_upsert_never_downgrades_an_already_verified_row(db: AsyncSession) -> None:
    """A human manually verifying a curated alias must not be silently
    reverted back to unverified by the next routine sync pass."""
    await sync_curated_aliases(db)
    rows = await _contracts(db)
    target = rows[0]
    target.verified = True
    await db.commit()

    await sync_curated_aliases(db)

    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.id == target.id)
    )).scalar_one()
    assert refreshed.verified is True


@pytest.mark.asyncio
async def test_sync_robinhood_filters_to_tracked_symbols_active_chain_4663(db: AsyncSession) -> None:
    nvda = (await db.execute(select(Asset).where(Asset.symbol == "NVDA"))).scalar_one()

    rh = _FakeRobinhood(items=[
        {"symbol": "NVDA", "chain_id": ROBINHOOD_CHAIN_ID, "contract_address": "0xNvdaToken", "active": True},
        {"symbol": "NVDA", "chain_id": 1, "contract_address": "0xWrongChain", "active": True},  # wrong chain
        {"symbol": "NVDA", "chain_id": ROBINHOOD_CHAIN_ID, "contract_address": "0xInactiveOne", "active": False},
        {"symbol": "NOTATRACKEDSTOCK", "chain_id": ROBINHOOD_CHAIN_ID, "contract_address": "0xUntracked", "active": True},
    ])
    counts = await sync_robinhood_stock_tokens(db, rh)

    assert counts["matched"] == 1
    rows = await _contracts(db)
    assert len(rows) == 1
    assert rows[0].contract_address == "0xnvdatoken"
    assert rows[0].asset_id == nvda.id
    assert rows[0].chain_id == ROBINHOOD_CHAIN_ID
    assert rows[0].contract_type == "robinhood_stock"
    # The registry's response schema is explicitly best-effort and not
    # reconfirmed against a live response — never auto-verified.
    assert rows[0].verified is False


@pytest.mark.asyncio
async def test_sync_robinhood_preserves_previous_rows_on_fetch_failure(db: AsyncSession) -> None:
    good_rh = _FakeRobinhood(items=[
        {"symbol": "NVDA", "chain_id": ROBINHOOD_CHAIN_ID, "contract_address": "0xNvdaToken", "active": True},
    ])
    await sync_robinhood_stock_tokens(db, good_rh)
    assert len(await _contracts(db)) == 1

    failing_rh = _FakeRobinhood(raise_error=True)
    counts = await sync_robinhood_stock_tokens(db, failing_rh)
    assert counts["failed"] is True
    assert len(await _contracts(db)) == 1


@pytest.mark.asyncio
async def test_verified_row_decimals_frozen_against_later_unverified_sync(db: AsyncSession) -> None:
    """A human confirming a token's real decimals (e.g. 6 for a USDC-like
    token CoinGecko guessed as 18) must survive every later sync pass that
    itself can't confirm that value — or wallet valuation could become
    wrong by orders of magnitude."""
    cg = _FakeCoinGecko(coins=[{"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xWBTCFAKE"}}])
    await sync_crypto_contracts_from_coingecko(db, cg)
    row = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xwbtcfake")
    )).scalar_one()
    row.verified = True
    row.decimals = 6  # human-confirmed real value, overriding the guessed 18
    await db.commit()

    # A later sync pass re-resolves the same address (still verified=False,
    # still the guessed default).
    await sync_crypto_contracts_from_coingecko(db, cg)

    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xwbtcfake")
    )).scalar_one()
    assert refreshed.decimals == 6
    assert refreshed.verified is True


@pytest.mark.asyncio
async def test_refused_reassignment_still_marked_touched_not_deactivated(db: AsyncSession) -> None:
    """A protected verified row (reassignment refused) must stay active —
    it was present in this run's response, so reconciliation must never
    treat it as "gone upstream" just because _upsert_contract refused to
    mutate it."""
    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()
    cg = _FakeCoinGecko(coins=[{"id": "ethereum", "symbol": "eth", "platforms": {"ethereum": "0xShared"}}])
    await sync_crypto_contracts_from_coingecko(db, cg)
    row = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xshared")
    )).scalar_one()
    row.verified = True
    row.asset_id = eth.id
    await db.commit()

    # Same run's response now resolves the SAME address to a different
    # asset (BTC) — refused, but the address is still "present upstream".
    cg2 = _FakeCoinGecko(coins=[{"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xShared"}}])
    counts = await sync_crypto_contracts_from_coingecko(db, cg2)

    assert counts["deactivated"] == 0
    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xshared")
    )).scalar_one()
    assert refreshed.active is True
    assert refreshed.asset_id == eth.id


@pytest.mark.asyncio
async def test_sync_native_gas_tokens_registers_eth_on_ethereum_and_base(db: AsyncSession) -> None:
    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()

    counts = await sync_native_gas_tokens(db)
    assert counts["contracts_written"] == 2

    rows = await _contracts(db)
    native_rows = [r for r in rows if r.contract_address == NATIVE]
    assert {r.chain_id for r in native_rows} == {ETHEREUM_CHAIN_ID, BASE_CHAIN_ID}
    for row in native_rows:
        assert row.asset_id == eth.id
        assert row.contract_type == "native"
        assert row.decimals == 18
        # 18 decimals for a native EVM gas token is a protocol constant,
        # not guessed data — verified directly, no human confirmation
        # needed, unlike every other source in this module.
        assert row.verified is True
        assert row.source == "native"


@pytest.mark.asyncio
async def test_sync_never_reassigns_a_verified_contract_to_a_different_asset(db: AsyncSession) -> None:
    """A contract address resolving to a different asset than before (an
    upstream data change) must never silently reassign a VERIFIED row —
    cached wallet positions already keyed to the old asset would be
    misvalued as the new one."""
    eth = (await db.execute(select(Asset).where(Asset.symbol == "ETH"))).scalar_one()

    cg = _FakeCoinGecko(coins=[{"id": "ethereum", "symbol": "eth", "platforms": {"ethereum": "0xShared"}}])
    await sync_crypto_contracts_from_coingecko(db, cg)
    row = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xshared")
    )).scalar_one()
    row.verified = True
    row.asset_id = eth.id
    await db.commit()

    # A later sync resolves the SAME address to a different asset (BTC).
    cg2 = _FakeCoinGecko(coins=[{"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xShared"}}])
    await sync_crypto_contracts_from_coingecko(db, cg2)

    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xshared")
    )).scalar_one()
    assert refreshed.asset_id == eth.id  # unchanged, never reassigned to btc.id
    assert refreshed.verified is True


@pytest.mark.asyncio
async def test_sync_deactivates_rows_no_longer_present_upstream(db: AsyncSession) -> None:
    """A contract removed from the upstream source between sync runs must
    be deactivated, not left active indefinitely (upsert-only sync never
    revisits it otherwise) — as long as the run overall still touched some
    real data (see test_sync_skips_reconciliation_on_wholly_empty_response
    for the "response was suspiciously empty" case, which must NOT
    deactivate anything)."""
    cg = _FakeCoinGecko(coins=[
        {"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xWillDisappear"}},
    ])
    await sync_crypto_contracts_from_coingecko(db, cg)
    row = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xwilldisappear")
    )).scalar_one()
    assert row.active is True

    # Next sync still returns real data (ETH matched) but no longer
    # includes BTC at all — a genuine, partial upstream change.
    cg2 = _FakeCoinGecko(coins=[
        {"id": "ethereum", "symbol": "eth", "platforms": {"ethereum": "0xEthAddr"}},
    ])
    counts = await sync_crypto_contracts_from_coingecko(db, cg2)
    assert counts["deactivated"] == 1

    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xwilldisappear")
    )).scalar_one()
    assert refreshed.active is False
    # Never deleted — cached wallet positions keep their asset mapping.
    assert refreshed.asset_id is not None


@pytest.mark.asyncio
async def test_sync_skips_reconciliation_on_wholly_empty_response(db: AsyncSession) -> None:
    """A technically-valid but wholly empty (or all-filtered-out) provider
    response must NEVER be trusted as "confirmed: everything from this
    source is gone now" — that would wipe out an entire source's catalogue
    on a transient hiccup. Only reconciles when there's at least one
    touched address as positive evidence this run saw real data."""
    cg = _FakeCoinGecko(coins=[
        {"id": "bitcoin", "symbol": "btc", "platforms": {"ethereum": "0xWillStay"}},
    ])
    await sync_crypto_contracts_from_coingecko(db, cg)

    # A wholly empty (but still validly-shaped) response next run.
    cg_empty = _FakeCoinGecko(coins=[])
    counts = await sync_crypto_contracts_from_coingecko(db, cg_empty)
    assert counts["deactivated"] == 0

    refreshed = (await db.execute(
        select(PortfolioContract).where(PortfolioContract.contract_address == "0xwillstay")
    )).scalar_one()
    assert refreshed.active is True


@pytest.mark.asyncio
async def test_sync_does_not_deactivate_rows_from_a_different_source(db: AsyncSession) -> None:
    """Reconciliation must only touch rows from the SAME source — a
    CoinGecko sync run must never deactivate a curated-alias row."""
    await sync_curated_aliases(db)
    alias_rows_before = [r for r in (await _contracts(db)) if r.source == "curated_alias"]
    assert alias_rows_before

    cg = _FakeCoinGecko(coins=[])
    await sync_crypto_contracts_from_coingecko(db, cg)

    alias_rows_after = [r for r in (await _contracts(db)) if r.source == "curated_alias"]
    assert all(r.active for r in alias_rows_after)
    assert len(alias_rows_after) == len(alias_rows_before)


@pytest.mark.asyncio
async def test_contract_identity_is_chain_plus_address_not_symbol(db: AsyncSession) -> None:
    """The exact same address string on two different chains must resolve
    to two distinct rows — never collapsed by address alone."""
    cg = _FakeCoinGecko(coins=[
        {"id": "ethereum", "symbol": "eth", "platforms": {"ethereum": "0xSameAddress", "base": "0xSameAddress"}},
    ])
    await sync_crypto_contracts_from_coingecko(db, cg)

    rows = await _contracts(db)
    assert len(rows) == 2
    assert {r.chain_id for r in rows} == {ETHEREUM_CHAIN_ID, BASE_CHAIN_ID}
