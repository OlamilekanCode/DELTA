"""Hand-verified tests for the Multicall3 aggregate3 ABI encoder/decoder.

No live chain available in this test suite, so correctness is proven two
ways: (1) structural assertions on the raw encoded bytes for known inputs,
and (2) a deliberately independent, from-scratch reference encoder (written
here, sharing no code with app.services.multicall) that builds a fake
on-chain response, which the real decoder must then parse correctly.
"""

from app.services.multicall import (
    MAX_CALLS_PER_BATCH,
    chunk_calls,
    decode_aggregate3_result,
    decode_balance_result,
    encode_aggregate3,
    encode_balance_of_calldata,
    multicall3_address_for_chain,
)

_ADDR_A = "0x" + "11" * 20
_ADDR_B = "0x" + "22" * 20
_WALLET = "0x" + "aa" * 20


def test_encode_balance_of_calldata_selector_and_length() -> None:
    calldata = encode_balance_of_calldata(_WALLET)
    assert len(calldata) == 36  # 4-byte selector + 32-byte address
    assert calldata[:4].hex() == "70a08231"
    assert calldata[4:].hex() == ("00" * 12) + ("aa" * 20)


def test_encode_aggregate3_single_call_structure() -> None:
    call_data = encode_balance_of_calldata(_WALLET)
    hex_calldata = encode_aggregate3([(_ADDR_A, call_data)])
    assert hex_calldata.startswith("0x82ad56cb")  # aggregate3 selector

    raw = bytes.fromhex(hex_calldata[2:])
    body = raw[4:]  # strip selector
    # word 0: offset to array = 0x20
    assert int.from_bytes(body[0:32], "big") == 32
    # word 1 (array start): length = 1
    assert int.from_bytes(body[32:64], "big") == 1
    # word 2: offset to tuple 0 within array data = 32 (1 element * 32)
    assert int.from_bytes(body[64:96], "big") == 32
    # tuple 0 starts at word 3 (byte 96 within body)
    tuple_start = 96
    target_word = body[tuple_start:tuple_start + 32]
    assert target_word[-20:].hex() == "11" * 20
    allow_failure = int.from_bytes(body[tuple_start + 32:tuple_start + 64], "big")
    assert allow_failure == 1
    call_data_offset = int.from_bytes(body[tuple_start + 64:tuple_start + 96], "big")
    assert call_data_offset == 96  # 3 head words
    call_data_len = int.from_bytes(
        body[tuple_start + call_data_offset: tuple_start + call_data_offset + 32], "big"
    )
    assert call_data_len == 36
    encoded_call_data = body[
        tuple_start + call_data_offset + 32: tuple_start + call_data_offset + 32 + call_data_len
    ]
    assert encoded_call_data == call_data


def test_encode_aggregate3_two_calls_offsets_are_sequential() -> None:
    call_data = encode_balance_of_calldata(_WALLET)
    hex_calldata = encode_aggregate3([(_ADDR_A, call_data), (_ADDR_B, call_data)])
    raw = bytes.fromhex(hex_calldata[2:])
    body = raw[4:]
    n = int.from_bytes(body[32:64], "big")
    assert n == 2
    offset_0 = int.from_bytes(body[64:96], "big")
    offset_1 = int.from_bytes(body[96:128], "big")
    # Each tuple (fixed-length callData) is 6 words = 192 bytes here.
    assert offset_0 == 2 * 32  # after the 2 head-offset words
    assert offset_1 == offset_0 + 192


def _reference_build_aggregate3_response(results: list[tuple[bool, int]]) -> str:
    """Independent, deliberately simple reference encoder for a fake
    `(bool,bytes)[]` aggregate3 response — every element's returnData here
    is a plain 32-byte uint256, so every tuple is exactly 4 words (128
    bytes), making per-element offsets trivial to compute by hand."""
    n = len(results)
    # Offsets are relative to the start of the elements section (right after
    # the length word), which begins with the N head-offset words
    # themselves — so element i's data starts at n*32 + i*128, not i*128.
    head = b"".join((n * 32 + i * 128).to_bytes(32, "big") for i in range(n))
    tail = b""
    for success, value in results:
        tail += (1 if success else 0).to_bytes(32, "big")
        tail += (64).to_bytes(32, "big")  # offset to bytes within this tuple
        tail += (32).to_bytes(32, "big")  # returnData length
        tail += value.to_bytes(32, "big")
    array_data = n.to_bytes(32, "big") + head + tail
    body = (32).to_bytes(32, "big") + array_data
    return "0x" + body.hex()


def test_decode_aggregate3_result_round_trip_against_independent_reference() -> None:
    fake_response = _reference_build_aggregate3_response([(True, 12345), (True, 999_999_999)])
    decoded = decode_aggregate3_result(fake_response, expected_count=2)
    assert len(decoded) == 2
    assert decoded[0][0] is True
    assert decode_balance_result(decoded[0][1]) == 12345
    assert decoded[1][0] is True
    assert decode_balance_result(decoded[1][1]) == 999_999_999


def test_decode_aggregate3_result_handles_per_call_failure() -> None:
    fake_response = _reference_build_aggregate3_response([(True, 500), (False, 0)])
    decoded = decode_aggregate3_result(fake_response, expected_count=2)
    assert decoded[0][0] is True
    assert decode_balance_result(decoded[0][1]) == 500
    assert decoded[1][0] is False


def test_decode_aggregate3_result_malformed_response_fails_closed() -> None:
    decoded = decode_aggregate3_result("0xdeadbeef", expected_count=3)
    assert decoded == [(False, b"")] * 3


def test_decode_aggregate3_result_truncated_response_fails_closed_for_missing() -> None:
    fake_response = _reference_build_aggregate3_response([(True, 1), (True, 2)])
    # Truncate to only cover the first element.
    truncated = fake_response[: len(fake_response) - 64]
    decoded = decode_aggregate3_result(truncated, expected_count=2)
    assert len(decoded) == 2
    assert decoded[1] == (False, b"")


def test_decode_balance_result_empty_bytes_is_none_not_zero() -> None:
    """Empty/malformed return data must never be read as a confirmed zero
    balance — the caller (wallet_reader.py) must be able to distinguish
    "unknown" from "genuinely holds zero"."""
    assert decode_balance_result(b"") is None


def test_decode_balance_result_short_bytes_is_none_not_zero() -> None:
    assert decode_balance_result(b"\x00" * 31) is None


def test_multicall3_address_uses_known_default_for_ethereum_and_base() -> None:
    assert multicall3_address_for_chain(1) == "0xca11bde05977b3631167028862be2a173976ca1"
    assert multicall3_address_for_chain(8453) == "0xca11bde05977b3631167028862be2a173976ca1"


def test_multicall3_address_unavailable_for_unconfirmed_chain() -> None:
    """Robinhood Chain's Multicall3 deployment has not been confirmed —
    batching must be unavailable there by default, never a guessed address."""
    assert multicall3_address_for_chain(4663) is None


def test_multicall3_address_override_wins_over_default() -> None:
    assert multicall3_address_for_chain(4663, override="0xABCDEF") == "0xabcdef"
    assert multicall3_address_for_chain(1, override="0x999999") == "0x999999"


def test_chunk_calls_splits_into_batch_size() -> None:
    calls = list(range(120))
    chunks = chunk_calls(calls, batch_size=50)
    assert len(chunks) == 3
    assert [len(c) for c in chunks] == [50, 50, 20]


def test_chunk_calls_default_batch_size_matches_constant() -> None:
    calls = list(range(MAX_CALLS_PER_BATCH + 1))
    chunks = chunk_calls(calls)
    assert len(chunks) == 2
