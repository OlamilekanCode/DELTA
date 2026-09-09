"""Version-controlled mapping of on-chain wallet assets to the Synthetic
Exposure catalogue, for portfolio position reading.

Every entry must be a confirmed, verified contract address — never a guess.
This list starts empty on Robinhood Chain because no contract addresses have
been confirmed yet; populate it (via a normal code change + PR, not a
runtime config value) once real addresses are available. An empty list is
not a bug — `refresh_wallet_positions` simply has nothing to read yet, and
the portfolio pipeline around it is fully implemented and tested against a
mocked RPC provider.
"""

from dataclasses import dataclass

NATIVE = "native"  # sentinel contract_address for a chain's gas token


@dataclass(frozen=True)
class PortfolioAssetContract:
    chain_id: int
    contract_address: str  # NATIVE for the chain's native gas token
    decimals: int
    symbol: str  # must match an Asset.symbol in the catalogue


# Populate with confirmed Robinhood Chain (and, if enabled, Ethereum/Base)
# contract addresses as they become available.
PORTFOLIO_ASSET_CONTRACTS: list[PortfolioAssetContract] = []


def contracts_for_chain(chain_id: int) -> list[PortfolioAssetContract]:
    return [c for c in PORTFOLIO_ASSET_CONTRACTS if c.chain_id == chain_id]
