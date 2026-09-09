"""Hand-rolled ABI encoding for batched ERC-20 `balanceOf` reads via the
Multicall3 standard contract (`aggregate3`), so a wallet refresh makes a
handful of RPC requests per chain instead of one per token.

No web3.py dependency, matching the rest of `services/blockchain.py` — the
two functions needed here (`aggregate3`, `balanceOf`) are simple enough to
encode/decode by hand, and this keeps the exact byte layout auditable and
unit-tested rather than hidden behind a library.

Multicall3 is deployed at the same address via CREATE2 on most EVM chains
(Ethereum, Base, and many others) — that address is trusted here as a
well-established public constant. Robinhood Chain is deliberately absent
from the default map: its Multicall3 deployment (if any) has not been
confirmed, so batching is unavailable there until an address is supplied.
"""

MULTICALL3_ADDRESSES: dict[int, str] = {
    1: "0xca11bde05977b3631167028862be2a173976ca1",  # Ethereum mainnet
    8453: "0xca11bde05977b3631167028862be2a173976ca1",  # Base
    # Robinhood Chain (4663) intentionally omitted — not yet confirmed.
}

_AGGREGATE3_SELECTOR = "82ad56cb"  # aggregate3((address,bool,bytes)[])
_BALANCE_OF_SELECTOR = "70a08231"  # balanceOf(address)

# Multicall3's per-call response payload can't exceed typical node response
# limits in one round trip — chunk large catalogues rather than risk a
# single oversized call.
MAX_CALLS_PER_BATCH = 50


def multicall3_address_for_chain(chain_id: int, override: str | None = None) -> str | None:
    """The Multicall3 contract address to use for a chain, or None if
    batching isn't available there. `override` (from configuration) always
    wins over the built-in default."""
    if override:
        return override.lower()
    return MULTICALL3_ADDRESSES.get(chain_id)


def _pad32(data: bytes) -> bytes:
    pad_len = (-len(data)) % 32
    return data + b"\x00" * pad_len


def _uint256(value: int) -> bytes:
    return value.to_bytes(32, "big")


def _encode_address(address: str) -> bytes:
    addr_hex = address.lower().removeprefix("0x").rjust(40, "0")
    return b"\x00" * 12 + bytes.fromhex(addr_hex)


def encode_balance_of_calldata(wallet_address: str) -> bytes:
    return bytes.fromhex(_BALANCE_OF_SELECTOR) + _encode_address(wallet_address)


def encode_aggregate3(calls: list[tuple[str, bytes]]) -> str:
    """`calls`: list of (target_contract_address, callData). allowFailure is
    always true — one reverting/nonexistent contract in the batch must
    never abort the whole multicall.

    Encodes the standard `(address target, bool allowFailure, bytes
    callData)[]` dynamic-array-of-dynamic-tuples ABI layout: a head section
    of per-element offsets followed by each tuple's own head (target,
    allowFailure, offset-to-callData) and tail (callData length + padded
    bytes).
    """
    n = len(calls)
    head_words: list[bytes] = []
    tail_blocks: list[bytes] = []
    running_offset = n * 32  # after the N per-element offset words
    for target, call_data in calls:
        tuple_tail = _uint256(len(call_data)) + _pad32(call_data)
        tuple_block = (
            _encode_address(target)
            + _uint256(1)  # allowFailure = true
            + _uint256(96)  # offset to callData within this tuple (3 head words * 32)
            + tuple_tail
        )
        head_words.append(_uint256(running_offset))
        tail_blocks.append(tuple_block)
        running_offset += len(tuple_block)

    array_data = _uint256(n) + b"".join(head_words) + b"".join(tail_blocks)
    args = _uint256(32) + array_data  # single top-level dynamic param -> offset 0x20
    calldata = bytes.fromhex(_AGGREGATE3_SELECTOR) + args
    return "0x" + calldata.hex()


def decode_aggregate3_result(hex_result: str, expected_count: int) -> list[tuple[bool, bytes]]:
    """Decode aggregate3's `(bool success, bytes returnData)[]` return
    value. A malformed/short response never raises — it's treated as every
    call having failed, so a caller can fail closed per-contract rather
    than crash the whole batch."""
    hex_result = hex_result[2:] if hex_result.startswith("0x") else hex_result
    try:
        data = bytes.fromhex(hex_result)
    except ValueError:
        return [(False, b"")] * expected_count
    if len(data) < 64:
        return [(False, b"")] * expected_count

    def _read_word(start: int) -> int | None:
        # bytes slicing never raises on out-of-range — a truncated response
        # silently returns a short slice, so length must be checked
        # explicitly rather than relying on an exception that never fires.
        if start < 0 or start + 32 > len(data):
            return None
        return int.from_bytes(data[start:start + 32], "big")

    array_offset = _read_word(0)
    if array_offset is None:
        return [(False, b"")] * expected_count
    n = _read_word(array_offset)
    if n is None:
        return [(False, b"")] * expected_count
    elements_base = array_offset + 32

    results: list[tuple[bool, bytes]] = []
    for i in range(min(n, expected_count)):
        tuple_rel_offset = _read_word(elements_base + i * 32)
        if tuple_rel_offset is None:
            results.append((False, b""))
            continue
        tuple_start = elements_base + tuple_rel_offset
        success_word = _read_word(tuple_start)
        return_data_rel_offset = _read_word(tuple_start + 32)
        if success_word is None or return_data_rel_offset is None:
            results.append((False, b""))
            continue
        return_data_start = tuple_start + return_data_rel_offset
        return_data_len = _read_word(return_data_start)
        if return_data_len is None or return_data_start + 32 + return_data_len > len(data):
            results.append((False, b""))
            continue
        success = success_word != 0
        return_data = data[return_data_start + 32: return_data_start + 32 + return_data_len]
        results.append((success, return_data))

    # A response shorter than expected (rare — a node truncating output)
    # fails closed for the missing entries rather than silently omitting them.
    while len(results) < expected_count:
        results.append((False, b""))
    return results


def decode_balance_result(return_data: bytes) -> int | None:
    """Returns None (never a confirmed 0) when `return_data` is shorter than
    the expected single uint256 word — a call reporting `success=True` but
    returning malformed/truncated data is not the same as a real, on-chain
    zero balance, and must never overwrite a previously-cached balance with
    one."""
    if len(return_data) < 32:
        return None
    return int.from_bytes(return_data[:32], "big")


def chunk_calls(calls: list, batch_size: int = MAX_CALLS_PER_BATCH) -> list[list]:
    return [calls[i:i + batch_size] for i in range(0, len(calls), batch_size)]


def decode_aggregate3_calldata(hex_data: str) -> list[tuple[str, bool, bytes]]:
    """Decode an `aggregate3` call's own calldata back into
    (target, allowFailure, callData) tuples — the inverse of
    encode_aggregate3. Not needed by the real RPC path (which only ever
    encodes, never decodes, its own outgoing request), but used by
    MockRpcProvider to realistically simulate a Multicall3 contract in
    tests without hand-building fake responses for every test."""
    hex_data = hex_data[2:] if hex_data.startswith("0x") else hex_data
    data = bytes.fromhex(hex_data)
    body = data[4:]  # strip the 4-byte selector

    def _read_word(start: int) -> int:
        return int.from_bytes(body[start:start + 32], "big")

    array_offset = _read_word(0)
    n = _read_word(array_offset)
    elements_base = array_offset + 32

    calls: list[tuple[str, bool, bytes]] = []
    for i in range(n):
        tuple_rel_offset = _read_word(elements_base + i * 32)
        tuple_start = elements_base + tuple_rel_offset
        target = "0x" + body[tuple_start + 12:tuple_start + 32].hex()
        allow_failure = _read_word(tuple_start + 32) != 0
        call_data_rel_offset = _read_word(tuple_start + 64)
        call_data_start = tuple_start + call_data_rel_offset
        call_data_len = _read_word(call_data_start)
        call_data = body[call_data_start + 32: call_data_start + 32 + call_data_len]
        calls.append((target, allow_failure, call_data))
    return calls


def decode_balance_of_calldata(call_data: bytes) -> str:
    """Extract the queried wallet address from a `balanceOf(address)`
    calldata blob (test/mock support — mirrors encode_balance_of_calldata)."""
    return "0x" + call_data[16:36].hex()
