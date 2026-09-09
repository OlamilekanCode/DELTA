"""Add portfolio_asset_contracts — the database-backed, verified contract-alias
catalogue replacing the static PORTFOLIO_ASSET_CONTRACTS list.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_asset_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("contract_type", sa.String(20), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "chain_id", "contract_address",
            name="uq_portfolio_contract_chain_address",
        ),
    )
    op.create_index("ix_portfolio_contract_asset_id", "portfolio_asset_contracts", ["asset_id"])
    op.create_index("ix_portfolio_contract_chain_id", "portfolio_asset_contracts", ["chain_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_contract_chain_id", table_name="portfolio_asset_contracts")
    op.drop_index("ix_portfolio_contract_asset_id", table_name="portfolio_asset_contracts")
    op.drop_table("portfolio_asset_contracts")
