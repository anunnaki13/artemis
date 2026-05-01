"""spot position pnl fields

Revision ID: 0012_spot_position_pnl_fields
Revises: 0011_spot_order_fill_states
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_spot_position_pnl_fields"
down_revision: str | None = "0011_spot_order_fill_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("spot_symbol_positions", sa.Column("last_mark_price", sa.Numeric(28, 12), nullable=True))
    op.add_column("spot_symbol_positions", sa.Column("market_value_usd", sa.Numeric(36, 18), nullable=True))
    op.add_column(
        "spot_symbol_positions",
        sa.Column("realized_pnl_usd", sa.Numeric(36, 18), nullable=False, server_default="0"),
    )
    op.add_column("spot_symbol_positions", sa.Column("unrealized_pnl_usd", sa.Numeric(36, 18), nullable=True))


def downgrade() -> None:
    op.drop_column("spot_symbol_positions", "unrealized_pnl_usd")
    op.drop_column("spot_symbol_positions", "realized_pnl_usd")
    op.drop_column("spot_symbol_positions", "market_value_usd")
    op.drop_column("spot_symbol_positions", "last_mark_price")
