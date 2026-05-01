"""spot execution fills

Revision ID: 0014_spot_exec_fills
Revises: 0013_intent_replacements
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_spot_exec_fills"
down_revision: str | None = "0013_intent_replacements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_execution_fills",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("client_order_id", sa.String(length=128), nullable=True),
        sa.Column("venue_order_id", sa.String(length=128), nullable=True),
        sa.Column("trade_id", sa.BigInteger(), nullable=True),
        sa.Column("quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("quote_quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("price", sa.Numeric(28, 12), nullable=False),
        sa.Column("realized_pnl_usd", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("post_fill_net_quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("post_fill_average_entry_price", sa.Numeric(28, 12), nullable=True),
        sa.Column("source_event", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_spot_execution_fills_symbol_filled_at", "spot_execution_fills", ["symbol", "filled_at"])
    op.create_index("ix_spot_execution_fills_client_order_id", "spot_execution_fills", ["client_order_id"])
    op.create_index("ix_spot_execution_fills_venue_order_id", "spot_execution_fills", ["venue_order_id"])


def downgrade() -> None:
    op.drop_index("ix_spot_execution_fills_venue_order_id", table_name="spot_execution_fills")
    op.drop_index("ix_spot_execution_fills_client_order_id", table_name="spot_execution_fills")
    op.drop_index("ix_spot_execution_fills_symbol_filled_at", table_name="spot_execution_fills")
    op.drop_table("spot_execution_fills")
