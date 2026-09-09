from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClaimedPurchaseTransaction(Base):
    """A verified $SynthEx/ETH purchase claim. Each tx_hash may be claimed once."""

    __tablename__ = "claimed_purchase_transactions"
    __table_args__ = (UniqueConstraint("tx_hash", name="uq_claimed_purchase_tx_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    block_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eth_spent_raw: Mapped[str] = mapped_column(String(78), nullable=False)  # wei, as decimal string
    eth_usd_price: Mapped[float] = mapped_column(Float, nullable=False)
    eth_usd_source_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usd_value_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    synthex_received_raw: Mapped[str] = mapped_column(String(78), nullable=False)  # raw token units
    router_address: Mapped[str] = mapped_column(String(42), nullable=False)
    pool_address: Mapped[str] = mapped_column(String(42), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
