"""orderbook snapshots

Revision ID: 0004_orderbook_snapshots
Revises: 0003_market_data_foundation
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_orderbook_snapshots"
down_revision: str | None = "0003_market_data_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orderbook_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_update_id", sa.BigInteger(), nullable=True),
        sa.Column("bids", postgresql.JSONB(), nullable=False),
        sa.Column("asks", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_orderbook_snapshots_symbol", "orderbook_snapshots", ["symbol"])
    op.create_index("ix_orderbook_snapshots_timestamp", "orderbook_snapshots", ["timestamp"])
    op.create_index(
        "ix_orderbook_snapshots_symbol_timestamp",
        "orderbook_snapshots",
        ["symbol", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_orderbook_snapshots_symbol_timestamp", table_name="orderbook_snapshots")
    op.drop_index("ix_orderbook_snapshots_timestamp", table_name="orderbook_snapshots")
    op.drop_index("ix_orderbook_snapshots_symbol", table_name="orderbook_snapshots")
    op.drop_table("orderbook_snapshots")
