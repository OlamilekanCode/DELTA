"""Add SIWE auth tables (auth_nonces, wallet_users, sessions) and cached_wallet_balances

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("wallet_address", name="uq_wallet_users_address"),
    )
    op.create_index("ix_wallet_users_address", "wallet_users", ["wallet_address"])

    op.create_table(
        "auth_nonces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("nonce", name="uq_auth_nonces_nonce"),
    )
    op.create_index("ix_auth_nonces_nonce", "auth_nonces", ["nonce"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "wallet_user_id",
            sa.Integer(),
            sa.ForeignKey("wallet_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_wallet_user_id", "sessions", ["wallet_user_id"])
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"])

    op.create_table(
        "cached_wallet_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("token_address", sa.String(42), nullable=False),
        sa.Column("balance_raw", sa.String(78), nullable=False),  # uint256 max = 78 digits
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_holder", sa.Boolean(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "wallet_address", "token_address", name="uq_cached_balance_wallet_token"
        ),
    )
    op.create_index("ix_cached_wallet_balances_wallet", "cached_wallet_balances", ["wallet_address"])


def downgrade() -> None:
    op.drop_table("cached_wallet_balances")
    op.drop_table("sessions")
    op.drop_table("auth_nonces")
    op.drop_table("wallet_users")
