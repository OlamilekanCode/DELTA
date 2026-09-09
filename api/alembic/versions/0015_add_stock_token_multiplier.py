"""Add current_multiplier to portfolio_asset_contracts, for applying
Robinhood Stock Token corporate-action adjustments to raw on-chain balances.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_asset_contracts") as batch_op:
        batch_op.add_column(sa.Column("current_multiplier", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio_asset_contracts") as batch_op:
        batch_op.drop_column("current_multiplier")
