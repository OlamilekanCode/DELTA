"""Add wallet_entitlements table for portfolio tier tracking

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("tier", sa.String(10), nullable=False, server_default="locked"),
        sa.Column("cumulative_usd_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("wallet_address", name="uq_wallet_entitlements_address"),
    )
    op.create_index("ix_wallet_entitlements_address", "wallet_entitlements", ["wallet_address"])


def downgrade() -> None:
    op.drop_table("wallet_entitlements")
