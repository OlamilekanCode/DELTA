"""add asset_quotes and stored_exposure_scores

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("market_cap_usd", sa.Float(), nullable=True),
        sa.Column("volume_24h_usd", sa.Float(), nullable=True),
        sa.Column("change_24h_pct", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="fixture"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_quotes_asset_id", "asset_quotes", ["asset_id"])

    op.create_table(
        "stored_exposure_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("crypto_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("raw_correlation", sa.Float(), nullable=False),
        sa.Column("observations", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["crypto_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_id", "crypto_id", name="uq_score_stock_crypto"),
    )
    op.create_index("ix_stored_scores_stock_id", "stored_exposure_scores", ["stock_id"])


def downgrade() -> None:
    op.drop_table("stored_exposure_scores")
    op.drop_table("asset_quotes")
