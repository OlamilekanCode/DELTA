"""Add intraday_prices and intraday_exposure_scores tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intraday_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("bucket_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("data_quality", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "interval", "bucket_ts", name="uq_intraday_asset_interval_bucket"),
    )
    op.create_index("ix_intraday_prices_asset_id", "intraday_prices", ["asset_id"])
    op.create_index("ix_intraday_prices_bucket_ts", "intraday_prices", ["bucket_ts"])

    op.create_table(
        "intraday_exposure_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("crypto_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("observations", sa.Integer(), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("window_sessions", sa.Integer(), nullable=False),
        sa.Column("data_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False, server_default="pearson_intraday_v1"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("data_quality", sa.String(20), nullable=False, server_default="ok"),
        sa.ForeignKeyConstraint(["stock_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crypto_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_id", "crypto_id", "interval", name="uq_intraday_score_stock_crypto_interval"),
    )
    op.create_index("ix_intraday_exposure_scores_stock_id", "intraday_exposure_scores", ["stock_id"])


def downgrade() -> None:
    op.drop_table("intraday_exposure_scores")
    op.drop_table("intraday_prices")
