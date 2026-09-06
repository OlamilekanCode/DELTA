"""Fix POL coingecko_id: matic-network → polygon-ecosystem-token

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-07
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE assets SET coingecko_id = 'polygon-ecosystem-token' "
        "WHERE symbol = 'POL' AND coingecko_id = 'matic-network'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE assets SET coingecko_id = 'matic-network' "
        "WHERE symbol = 'POL' AND coingecko_id = 'polygon-ecosystem-token'"
    )
