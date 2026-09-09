from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StoredExposureScore(Base):
    __tablename__ = "stored_exposure_scores"
    __table_args__ = (UniqueConstraint("stock_id", "crypto_id", name="uq_score_stock_crypto"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crypto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    raw_correlation: Mapped[float] = mapped_column(Float, nullable=False)
    observations: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_quality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Comma-separated combination of zero or more flags (never mutually
    # exclusive — e.g. "crypto_daily_proxy,adj_close_missing"):
    # "crypto_daily_proxy" (crypto side is a daily UTC close, not selected
    # against the actual XNYS session close — see docs/methodology.md) |
    # "adj_close_missing" | "low_observations"
    data_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
