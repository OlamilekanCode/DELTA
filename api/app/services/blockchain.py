"""Minimal JSON-RPC client for reading ERC-20 balances and transaction data on
Robinhood Chain (EVM). Server-only — `ROBINHOOD_RPC_URL` never reaches the
frontend. No web3.py dependency: the calls needed here (eth_chainId,
eth_call, eth_blockNumber, eth_getTransactionByHash, eth_getTransactionReceipt,
eth_getBlockByNumber) are a handful of plain JSON-RPC requests, encoded and
decoded by hand to keep the dependency surface small.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

_ERC20_BALANCE_OF_SELECTOR = "0x70a08231"


class RpcError(Exception):
    pass


@dataclass
class TransactionData:
    hash: str
    from_address: str
    to_address: str | None
    value_wei: int
    block_number: int | None
    input_data: str


@dataclass
class TransactionReceipt:
    status: int  # 1 = success, 0 = reverted
    block_number: int
    logs: list[dict]  # raw JSON-RPC log entries: {"address", "topics", "data"}


@dataclass
class BlockData:
    number: int
    timestamp: int  # unix seconds


class RpcProvider(Protocol):
    async def get_chain_id(self) -> int: ...
    async def get_block_number(self) -> int: ...
    async def get_erc20_balance(self, token_address: str, wallet_address: str) -> int: ...
    async def get_native_balance(self, wallet_address: str) -> int: ...
    async def get_transaction(self, tx_hash: str) -> TransactionData | None: ...
    async def get_transaction_receipt(self, tx_hash: str) -> TransactionReceipt | None: ...
    async def get_block(self, block_number: int) -> BlockData | None: ...


def _pad_address(address: str) -> str:
    return address.lower().replace("0x", "").rjust(64, "0")


def _hex_to_int(value: str | None) -> int:
    if not value or value == "0x":
        return 0
    return int(value, 16)


class JsonRpcProvider:
    """Real JSON-RPC implementation over `ROBINHOOD_RPC_URL`. Never exposed to
    the frontend — used only from server-side entitlement/purchase services."""

    def __init__(self, rpc_url: str, timeout: float = 10.0) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout

    async def _call(self, method: str, params: list) -> object:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(self.rpc_url, json=payload)
        if r.status_code != 200:
            raise RpcError(f"RPC HTTP {r.status_code}")
        body = r.json()
        if "error" in body:
            raise RpcError(f"RPC error: {body['error']}")
        return body.get("result")

    async def get_chain_id(self) -> int:
        result = await self._call("eth_chainId", [])
        return _hex_to_int(result)

    async def get_block_number(self) -> int:
        result = await self._call("eth_blockNumber", [])
        return _hex_to_int(result)

    async def get_erc20_balance(self, token_address: str, wallet_address: str) -> int:
        data = _ERC20_BALANCE_OF_SELECTOR + _pad_address(wallet_address)
        result = await self._call("eth_call", [{"to": token_address, "data": data}, "latest"])
        return _hex_to_int(result)

    async def get_native_balance(self, wallet_address: str) -> int:
        result = await self._call("eth_getBalance", [wallet_address, "latest"])
        return _hex_to_int(result)

    async def get_transaction(self, tx_hash: str) -> TransactionData | None:
        result = await self._call("eth_getTransactionByHash", [tx_hash])
        if not result:
            return None
        return TransactionData(
            hash=result["hash"],
            from_address=result["from"].lower(),
            to_address=result["to"].lower() if result.get("to") else None,
            value_wei=_hex_to_int(result.get("value")),
            block_number=_hex_to_int(result["blockNumber"]) if result.get("blockNumber") else None,
            input_data=result.get("input", "0x"),
        )

    async def get_transaction_receipt(self, tx_hash: str) -> TransactionReceipt | None:
        result = await self._call("eth_getTransactionReceipt", [tx_hash])
        if not result:
            return None
        return TransactionReceipt(
            status=_hex_to_int(result.get("status")),
            block_number=_hex_to_int(result["blockNumber"]),
            logs=result.get("logs", []),
        )

    async def get_block(self, block_number: int) -> BlockData | None:
        result = await self._call("eth_getBlockByNumber", [hex(block_number), False])
        if not result:
            return None
        return BlockData(number=_hex_to_int(result["number"]), timestamp=_hex_to_int(result["timestamp"]))


class MockRpcProvider:
    """In-memory RPC double for tests and local development without a real
    Robinhood Chain RPC endpoint configured."""

    def __init__(
        self,
        chain_id: int = 0,
        block_number: int = 1_000_000,
        balances: dict[tuple[str, str], int] | None = None,
        native_balances: dict[str, int] | None = None,
        transactions: dict[str, TransactionData] | None = None,
        receipts: dict[str, TransactionReceipt] | None = None,
        blocks: dict[int, BlockData] | None = None,
        raise_on_call: Exception | None = None,
    ) -> None:
        self.chain_id = chain_id
        self.block_number = block_number
        self.balances = balances or {}
        self.native_balances = native_balances or {}
        self.transactions = transactions or {}
        self.receipts = receipts or {}
        self.blocks = blocks or {}
        self.raise_on_call = raise_on_call

    def _maybe_raise(self) -> None:
        if self.raise_on_call is not None:
            raise self.raise_on_call

    async def get_chain_id(self) -> int:
        self._maybe_raise()
        return self.chain_id

    async def get_block_number(self) -> int:
        self._maybe_raise()
        return self.block_number

    async def get_erc20_balance(self, token_address: str, wallet_address: str) -> int:
        self._maybe_raise()
        return self.balances.get((token_address.lower(), wallet_address.lower()), 0)

    async def get_native_balance(self, wallet_address: str) -> int:
        self._maybe_raise()
        return self.native_balances.get(wallet_address.lower(), 0)

    async def get_transaction(self, tx_hash: str) -> TransactionData | None:
        self._maybe_raise()
        return self.transactions.get(tx_hash.lower())

    async def get_transaction_receipt(self, tx_hash: str) -> TransactionReceipt | None:
        self._maybe_raise()
        return self.receipts.get(tx_hash.lower())

    async def get_block(self, block_number: int) -> BlockData | None:
        self._maybe_raise()
        return self.blocks.get(block_number)
