"""spot order fill states

Revision ID: 0011_spot_order_fill_states
Revises: 0010_spot_symbol_positions
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_spot_order_fill_states"
down_revision: str | None = "0010_spot_symbol_positions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_order_fill_states",
        sa.Column("order_key", sa.String(length=160), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("client_order_id", sa.String(length=128), nullable=True),
        sa.Column("venue_order_id", sa.String(length=128), nullable=True),
        sa.Column("cumulative_quantity", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("cumulative_quote_quantity", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("last_trade_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source_event", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_spot_order_fill_states_updated_at", "spot_order_fill_states", ["updated_at"])
    op.create_index(
        "ix_spot_order_fill_states_client_order_id",
        "spot_order_fill_states",
        ["client_order_id"],
    )
    op.create_index(
        "ix_spot_order_fill_states_venue_order_id",
        "spot_order_fill_states",
        ["venue_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_spot_order_fill_states_venue_order_id", table_name="spot_order_fill_states")
    op.drop_index("ix_spot_order_fill_states_client_order_id", table_name="spot_order_fill_states")
    op.drop_index("ix_spot_order_fill_states_updated_at", table_name="spot_order_fill_states")
    op.drop_table("spot_order_fill_states")
