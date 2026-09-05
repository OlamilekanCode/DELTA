from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("symbol", name="uq_assets_symbol"),
        UniqueConstraint("coingecko_id", name="uq_assets_coingecko_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "stock" | "crypto"
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    coingecko_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
