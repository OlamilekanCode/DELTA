from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WalletUser(Base):
    __tablename__ = "wallet_users"
    __table_args__ = (UniqueConstraint("wallet_address", name="uq_wallet_users_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)  # lowercase 0x...
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthNonce(Base):
    __tablename__ = "auth_nonces"
    __table_args__ = (UniqueConstraint("nonce", name="uq_auth_nonces_nonce"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_sessions_token_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wallet_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # sha256 hex digest
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CachedWalletBalance(Base):
    """Server-cached $SynthEx holder status per wallet, refreshed from on-chain reads.

    Never queried live per-request — refreshed on login/wallet-change/purchase/interval
    (see entitlements.refresh) and read here with a short freshness window.
    """

    __tablename__ = "cached_wallet_balances"
    __table_args__ = (
        UniqueConstraint("wallet_address", "token_address", name="uq_cached_balance_wallet_token"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    token_address: Mapped[str] = mapped_column(String(42), nullable=False)
    balance_raw: Mapped[str] = mapped_column(String(78), nullable=False)  # uint256 as decimal string
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_holder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
