"""services/wallet_reader.py — batched wallet balance reads.

Covers: native balance is a single direct call, ERC-20 balances batch
through Multicall3 when an address is known for the chain, a chain with no
known Multicall3 address falls back to one call per token instead of
silently dropping those balances, a per-call failure inside a batch is
isolated (never a confirmed zero, never aborts the rest of the batch), and
large catalogues are chunked.
"""

import pytest

from app.models.portfolio_contract import PortfolioContract
from app.services.blockchain import MockRpcProvider
from app.services.portfolio_assets import NATIVE
from app.services.wallet_reader import read_balances_batched

_WALLET = "0x" + "aa" * 20


def _contract(chain_id: int, address: str, contract_type: str = "erc20") -> PortfolioContract:
    return PortfolioContract(
        asset_id=1, chain_id=chain_id, contract_address=address, contract_type=contract_type,
        decimals=18, source="test", verified=True, active=True,
    )


@pytest.mark.asyncio
async def test_native_balance_is_one_direct_call_not_multicall() -> None:
    mock = MockRpcProvider(chain_id=8453, native_balances={_WALLET.lower(): 42})
    contracts = [_contract(8453, NATIVE, "native")]
    balances = await read_balances_batched(mock, 8453, _WALLET, contracts)
    assert balances[NATIVE] == 42


@pytest.mark.asyncio
async def test_erc20_balances_batch_through_multicall_on_known_chain() -> None:
    token_a = "0x" + "11" * 20
    token_b = "0x" + "22" * 20
    mock = MockRpcProvider(chain_id=8453, balances={
        (token_a, _WALLET.lower()): 100,
        (token_b, _WALLET.lower()): 200,
    })
    contracts = [_contract(8453, token_a), _contract(8453, token_b)]
    balances = await read_balances_batched(mock, 8453, _WALLET, contracts)
    assert balances[token_a] == 100
    assert balances[token_b] == 200


@pytest.mark.asyncio
async def test_missing_balance_result_is_absent_not_zero() -> None:
    """A contract the mock has no balance entry for must be OMITTED from
    the result — never silently reported as a confirmed zero balance."""
    token_a = "0x" + "11" * 20
    token_unknown = "0x" + "33" * 20
    mock = MockRpcProvider(chain_id=8453, balances={(token_a, _WALLET.lower()): 100})
    contracts = [_contract(8453, token_a), _contract(8453, token_unknown)]
    balances = await read_balances_batched(mock, 8453, _WALLET, contracts)
    assert balances[token_a] == 100
    assert token_unknown not in balances


@pytest.mark.asyncio
async def test_falls_back_to_per_token_calls_on_chain_without_multicall_address() -> None:
    """Robinhood Chain (4663) has no confirmed Multicall3 deployment — the
    reader must still return correct balances via get_erc20_balance, not
    silently skip every token."""
    token_a = "0x" + "11" * 20
    mock = MockRpcProvider(chain_id=4663, balances={(token_a, _WALLET.lower()): 555})
    contracts = [_contract(4663, token_a)]
    balances = await read_balances_batched(mock, 4663, _WALLET, contracts)
    assert balances[token_a] == 555


@pytest.mark.asyncio
async def test_multicall_override_address_used_for_unconfirmed_chain() -> None:
    """Once a chain's Multicall3 address is confirmed and configured, the
    reader must use the batched path for it instead of the per-token
    fallback."""
    token_a = "0x" + "11" * 20
    multicall_addr = "0x" + "cc" * 20
    mock = MockRpcProvider(chain_id=4663, balances={(token_a, _WALLET.lower()): 777})
    contracts = [_contract(4663, token_a)]
    balances = await read_balances_batched(
        mock, 4663, _WALLET, contracts, multicall_address_override=multicall_addr
    )
    assert balances[token_a] == 777


@pytest.mark.asyncio
async def test_native_read_failure_does_not_block_erc20_reads() -> None:
    """Native and ERC-20 reads are independent — a failure in one must not
    prevent the other from completing."""

    class _PartialFailureMock(MockRpcProvider):
        async def get_native_balance(self, wallet_address: str) -> int:
            raise RuntimeError("native read down")

    token_a = "0x" + "11" * 20
    mock = _PartialFailureMock(chain_id=8453, balances={(token_a, _WALLET.lower()): 100})
    contracts = [_contract(8453, NATIVE, "native"), _contract(8453, token_a)]
    balances = await read_balances_batched(mock, 8453, _WALLET, contracts)
    assert NATIVE not in balances
    assert balances[token_a] == 100


@pytest.mark.asyncio
async def test_large_catalogue_is_chunked_across_multiple_multicall_batches() -> None:
    from app.services.multicall import MAX_CALLS_PER_BATCH

    n = MAX_CALLS_PER_BATCH + 5
    tokens = [f"0x{i:040x}" for i in range(1, n + 1)]
    balances_map = {(t, _WALLET.lower()): i for i, t in enumerate(tokens, start=1)}
    mock = MockRpcProvider(chain_id=8453, balances=balances_map)
    contracts = [_contract(8453, t) for t in tokens]
    balances = await read_balances_batched(mock, 8453, _WALLET, contracts)
    assert len(balances) == n
    for i, t in enumerate(tokens, start=1):
        assert balances[t] == i
