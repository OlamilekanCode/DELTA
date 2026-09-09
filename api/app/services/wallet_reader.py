"""Batched on-chain wallet balance reads via Multicall3 — a handful of RPC
requests per configured chain instead of one per token.
"""

import logging

from app.models.portfolio_contract import PortfolioContract
from app.services.blockchain import RpcProvider
from app.services.multicall import (
    chunk_calls,
    decode_aggregate3_result,
    decode_balance_result,
    encode_aggregate3,
    encode_balance_of_calldata,
    multicall3_address_for_chain,
)
from app.services.portfolio_assets import NATIVE

log = logging.getLogger(__name__)


async def read_balances_batched(
    rpc: RpcProvider,
    chain_id: int,
    wallet_address: str,
    contracts: list[PortfolioContract],
    multicall_address_override: str | None = None,
) -> dict[str, int]:
    """Returns {contract_address: raw_balance} for every contract that
    could be successfully read. A contract missing from the result means
    its read failed or was skipped — callers must treat a missing key as
    "unknown", never as a confirmed zero balance.

    Native gas-token balance is always one direct `get_native_balance` call
    (there's nothing to batch — a wallet has exactly one native balance per
    chain). ERC-20 balances batch through Multicall3's `aggregate3` when an
    address is available for the chain; otherwise this falls back to one
    `eth_call` per token (still correct, just not batched) rather than
    silently dropping those balances.
    """
    balances: dict[str, int] = {}

    native_contracts = [c for c in contracts if c.contract_address == NATIVE]
    erc20_contracts = [c for c in contracts if c.contract_address != NATIVE]

    if native_contracts:
        try:
            native_balance = await rpc.get_native_balance(wallet_address)
            for c in native_contracts:
                balances[c.contract_address] = native_balance
        except Exception:
            log.exception("Native balance read failed for chain %s", chain_id)

    if not erc20_contracts:
        return balances

    multicall_address = multicall3_address_for_chain(chain_id, multicall_address_override)
    if multicall_address is None:
        log.warning(
            "No Multicall3 address available for chain %s — falling back to one "
            "eth_call per token (%d tokens)", chain_id, len(erc20_contracts),
        )
        for c in erc20_contracts:
            try:
                balances[c.contract_address] = await rpc.get_erc20_balance(c.contract_address, wallet_address)
            except Exception:
                log.exception("Balance read failed for %s on chain %s", c.contract_address, chain_id)
        return balances

    call_data = encode_balance_of_calldata(wallet_address)
    for batch in chunk_calls(erc20_contracts):
        calls = [(c.contract_address, call_data) for c in batch]
        try:
            hex_result = await rpc.eth_call(multicall_address, encode_aggregate3(calls))
        except Exception:
            log.exception(
                "Multicall batch read failed for chain %s (%d tokens in batch)", chain_id, len(batch)
            )
            continue
        decoded = decode_aggregate3_result(hex_result, expected_count=len(batch))
        for contract, (success, return_data) in zip(batch, decoded, strict=True):
            if success:
                balance = decode_balance_result(return_data)
                if balance is not None:
                    balances[contract.contract_address] = balance
                else:
                    log.warning(
                        "Malformed balanceOf return data for %s on chain %s — "
                        "leaving balance unknown rather than a confirmed zero",
                        contract.contract_address, chain_id,
                    )
            # else: leave missing — a failed per-call read (allowFailure)
            # is not a confirmed zero balance.
    return balances
