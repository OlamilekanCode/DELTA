from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IntradayPrice(Base):
    __tablename__ = "intraday_prices"
    __table_args__ = (
        UniqueConstraint("asset_id", "interval", "bucket_ts", name="uq_intraday_asset_interval_bucket"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bucket_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "30m"
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")  # "ok" | "reduced"
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
