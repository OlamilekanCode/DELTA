from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IntradayExposureScore(Base):
    __tablename__ = "intraday_exposure_scores"
    __table_args__ = (
        UniqueConstraint("stock_id", "crypto_id", "interval", name="uq_intraday_score_stock_crypto_interval"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crypto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)       # signed Pearson r [-1, +1]
    observations: Mapped[int] = mapped_column(Integer, nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "30m"
    window_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    data_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False, default="pearson_intraday_v1")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
