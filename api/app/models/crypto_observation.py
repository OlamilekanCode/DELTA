from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CryptoQuoteObservation(Base):
    """A single timestamped crypto price sample from the 5-minute quote job.

    Used only to build 30-minute intraday candles (see services/intraday.py)
    — never queried per-request. Retained 7 days (see ingestion/commands.py
    cmd_cleanup_old_data); 30-minute candles derived from these are retained
    separately and much longer.
    """

    __tablename__ = "crypto_quote_observations"
    __table_args__ = (
        UniqueConstraint("asset_id", "ts", name="uq_crypto_quote_obs_asset_ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
