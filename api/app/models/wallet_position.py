from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CachedWalletPosition(Base):
    """A cached on-chain balance for one supported portfolio asset, for one wallet.

    Refreshed only on explicit/background refresh (see services/portfolio.py)
    — never read live per portfolio-page visit. `asset_id` is null when the
    position is for a chain/asset not yet linked to the Synthetic Exposure
    catalogue (still stored for completeness, excluded from exposure math).
    """

    __tablename__ = "cached_wallet_positions"
    __table_args__ = (
        UniqueConstraint(
            "wallet_address", "chain_id", "contract_address",
            name="uq_wallet_position_wallet_chain_contract",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)  # "native" for the gas token
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    quantity_raw: Mapped[str] = mapped_column(String(78), nullable=False)  # integer units, as decimal string
    decimals: Mapped[int] = mapped_column(Integer, nullable=False)
    usd_value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
