"""Add adj_close and score data-quality metadata

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("daily_prices") as batch_op:
        batch_op.add_column(sa.Column("adj_close", sa.Float(), nullable=True))

    with op.batch_alter_table("stored_exposure_scores") as batch_op:
        batch_op.add_column(sa.Column("data_quality", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("data_ts", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("stored_exposure_scores") as batch_op:
        batch_op.drop_column("data_ts")
        batch_op.drop_column("data_quality")

    with op.batch_alter_table("daily_prices") as batch_op:
        batch_op.drop_column("adj_close")
