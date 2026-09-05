"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-04

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("asset_type", sa.String(length=10), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("coingecko_id", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coingecko_id", name="uq_assets_coingecko_id"),
        sa.UniqueConstraint("symbol", name="uq_assets_symbol"),
    )
    op.create_index("ix_assets_symbol", "assets", ["symbol"])

    op.create_table(
        "daily_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "date", name="uq_daily_prices_asset_date"),
    )
    op.create_index("ix_daily_prices_asset_date", "daily_prices", ["asset_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_daily_prices_asset_date", table_name="daily_prices")
    op.drop_table("daily_prices")
    op.drop_index("ix_assets_symbol", table_name="assets")
    op.drop_table("assets")
