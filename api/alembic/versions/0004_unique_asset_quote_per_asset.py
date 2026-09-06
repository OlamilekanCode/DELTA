"""add unique constraint: one quote row per asset

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate rows, keeping the most recent per asset_id
    op.execute(
        "DELETE FROM asset_quotes "
        "WHERE id NOT IN ("
        "  SELECT MAX(id) FROM asset_quotes GROUP BY asset_id"
        ")"
    )
    # batch_alter_table is required for SQLite, which cannot add constraints via
    # plain ALTER TABLE.  It is a no-op on PostgreSQL.
    with op.batch_alter_table("asset_quotes", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_asset_quotes_asset_id", ["asset_id"])


def downgrade() -> None:
    with op.batch_alter_table("asset_quotes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_asset_quotes_asset_id", type_="unique")
