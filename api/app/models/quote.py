from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AssetQuote(Base):
    __tablename__ = "asset_quotes"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_asset_quotes_asset_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    market_cap_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24h_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_24h_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="fixture")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
