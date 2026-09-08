"""$SynthEx/ETH purchase verification. Fail-closed by design: until Robinhood
Chain's RPC URL, router/pool addresses and token contract are supplied via
environment variables, no purchase can ever be verified — this function must
never fabricate a successful verification or invent configuration values.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.purchase import ClaimedPurchaseTransaction

NOT_CONFIGURED = {
    "status": "not_configured",
    "message": "Purchase verification is not configured yet",
}


async def verify_purchase(db: AsyncSession, wallet_address: str, tx_hash: str) -> dict:
    settings = get_settings()
    if (
        settings.synthex_chain_id == 0
        or not settings.robinhood_rpc_url
        or not settings.synthex_token_address
    ):
        return dict(NOT_CONFIGURED)

    existing = await db.execute(
        select(ClaimedPurchaseTransaction).where(ClaimedPurchaseTransaction.tx_hash == tx_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return {"status": "already_claimed", "message": "This transaction has already been claimed"}

    # Real verification (fetch the tx receipt over settings.robinhood_rpc_url,
    # confirm required confirmations, confirm the router/pool + $SynthEx
    # contract addresses, compute net ETH/WETH spent, look up the ETH/USD
    # price at the block timestamp, and persist a ClaimedPurchaseTransaction
    # row) is intentionally not implemented: there is no real RPC URL, router,
    # pool or contract address to build or test it against, and inventing one
    # would violate the fail-closed requirement. Once real configuration is
    # supplied, this branch replaces the line below.
    return dict(NOT_CONFIGURED)
