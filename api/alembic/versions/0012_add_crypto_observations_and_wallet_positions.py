"""Add crypto_quote_observations, cached_wallet_positions, and
cached_wallet_balances.checked_block_number

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crypto_quote_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("asset_id", "ts", name="uq_crypto_quote_obs_asset_ts"),
    )
    op.create_index("ix_crypto_quote_obs_asset_id", "crypto_quote_observations", ["asset_id"])
    op.create_index("ix_crypto_quote_obs_ts", "crypto_quote_observations", ["ts"])

    op.create_table(
        "cached_wallet_positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity_raw", sa.String(78), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False),
        sa.Column("usd_value_cents", sa.Integer(), nullable=True),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "wallet_address", "chain_id", "contract_address",
            name="uq_wallet_position_wallet_chain_contract",
        ),
    )
    op.create_index("ix_wallet_position_wallet_address", "cached_wallet_positions", ["wallet_address"])

    with op.batch_alter_table("cached_wallet_balances") as batch_op:
        batch_op.add_column(sa.Column("checked_block_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("cached_wallet_balances") as batch_op:
        batch_op.drop_column("checked_block_number")

    op.drop_index("ix_wallet_position_wallet_address", table_name="cached_wallet_positions")
    op.drop_table("cached_wallet_positions")

    op.drop_index("ix_crypto_quote_obs_ts", table_name="crypto_quote_observations")
    op.drop_index("ix_crypto_quote_obs_asset_id", table_name="crypto_quote_observations")
    op.drop_table("crypto_quote_observations")
