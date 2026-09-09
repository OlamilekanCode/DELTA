from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioContract(Base):
    """A verified on-chain contract alias for a Synthetic Exposure asset —
    the database-backed replacement for the old static
    services/portfolio_assets.PORTFOLIO_ASSET_CONTRACTS list.

    Populated only by the catalogue-sync job (see
    ingestion/commands.py:cmd_refresh_portfolio_catalogue), never by a
    runtime config value or a client request. Identity is always
    (chain_id, contract_address) — a token symbol alone is never trusted to
    resolve a contract.

    `verified` gates whether the batch wallet reader will actually query a
    row. Every source defaults to verified=False and requires a human to
    flip it on after independently confirming the contract against a block
    explorer — exactly the existing ROUTER_ADAPTERS "confirmed, never
    guessed" convention:

    - CoinGecko's coins/list endpoint has no per-platform decimals field,
      so `decimals` there is an assumed default, not a confirmed value —
      trusting it blind risks misvaluing a holding by orders of magnitude.
    - Robinhood's asset registry schema is explicitly best-effort/unconfirmed
      (see providers/robinhood.py's module docstring).
    - Curated wrapped-token aliases are hardcoded from memory, not a live
      provider response.

    The one exception is `contract_type="native"` rows (the chain's own gas
    token, e.g. ETH on Ethereum/Base) — decimals=18 there is an EVM
    protocol constant, not app-specific guessed data, so those are marked
    verified=True at sync time.
    """

    __tablename__ = "portfolio_asset_contracts"
    __table_args__ = (
        UniqueConstraint(
            "chain_id", "contract_address",
            name="uq_portfolio_contract_chain_address",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)  # "native" sentinel for gas token
    contract_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "native" | "erc20" | "robinhood_stock"
    decimals: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    # "coingecko" | "robinhood" | "curated_alias"
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Robinhood Stock Token corporate-action multiplier (splits/reverse
    # splits) — synced from the same registry as the contract address.
    # Only balanceOf() is called on-chain (see services/wallet_reader.py);
    # balanceOfUI()'s selector has not been confirmed against a live
    # contract, so this multiplier is applied client-side at valuation
    # time (services/portfolio.py) instead of trusting an unverified
    # on-chain call. None for non-stock-token contracts.
    current_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
