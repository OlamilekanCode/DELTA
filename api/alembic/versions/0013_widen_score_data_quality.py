"""Widen stored_exposure_scores.data_quality to hold multiple comma-separated
quality flags (e.g. "crypto_daily_proxy,adj_close_missing") instead of a
single mutually-exclusive value.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("stored_exposure_scores") as batch_op:
        batch_op.alter_column(
            "data_quality",
            existing_type=sa.String(30),
            type_=sa.String(120),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("stored_exposure_scores") as batch_op:
        batch_op.alter_column(
            "data_quality",
            existing_type=sa.String(120),
            type_=sa.String(30),
            existing_nullable=True,
        )
