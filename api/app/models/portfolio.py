from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WalletEntitlement(Base):
    """Server-side tier derived from verified cumulative $SynthEx/ETH purchase value.

    Tier is only ever raised by a verified purchase claim and only ever lowered
    by the current holder balance dropping below the required amount (see
    services/portfolio.py) — never by passive price movement alone.
    """

    __tablename__ = "wallet_entitlements"
    __table_args__ = (UniqueConstraint("wallet_address", name="uq_wallet_entitlements_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(10), nullable=False, default="locked")
    # "locked" | "summary" | "detailed" | "premium"
    cumulative_usd_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
