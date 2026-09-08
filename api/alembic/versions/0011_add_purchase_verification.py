"""Add claimed_purchase_transactions table

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claimed_purchase_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("tx_hash", sa.String(66), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eth_spent_raw", sa.String(78), nullable=False),
        sa.Column("eth_usd_price", sa.Float(), nullable=False),
        sa.Column("eth_usd_source_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usd_value_cents", sa.Integer(), nullable=False),
        sa.Column("synthex_received_raw", sa.String(78), nullable=False),
        sa.Column("router_address", sa.String(42), nullable=False),
        sa.Column("pool_address", sa.String(42), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tx_hash", name="uq_claimed_purchase_tx_hash"),
    )
    op.create_index(
        "ix_claimed_purchase_wallet", "claimed_purchase_transactions", ["wallet_address"]
    )


def downgrade() -> None:
    op.drop_table("claimed_purchase_transactions")
