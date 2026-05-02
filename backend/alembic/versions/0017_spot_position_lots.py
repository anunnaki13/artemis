"""spot position lots

Revision ID: 0017_spot_position_lots
Revises: 0016_daily_digest_runs
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_spot_position_lots"
down_revision: str | None = "0016_daily_digest_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_position_lots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("execution_intent_id", sa.BigInteger(), nullable=True),
        sa.Column("source_strategy", sa.String(length=64), nullable=True),
        sa.Column("client_order_id", sa.String(length=128), nullable=True),
        sa.Column("venue_order_id", sa.String(length=128), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("original_quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("source_event", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spot_position_lots_symbol", "spot_position_lots", ["symbol"])
    op.create_index("ix_spot_position_lots_execution_intent_id", "spot_position_lots", ["execution_intent_id"])
    op.create_index("ix_spot_position_lots_opened_at", "spot_position_lots", ["opened_at"])
    op.create_index("ix_spot_position_lots_symbol_opened_at", "spot_position_lots", ["symbol", "opened_at"])
    op.create_index("ix_spot_position_lots_remaining_quantity", "spot_position_lots", ["remaining_quantity"])


def downgrade() -> None:
    op.drop_index("ix_spot_position_lots_remaining_quantity", table_name="spot_position_lots")
    op.drop_index("ix_spot_position_lots_symbol_opened_at", table_name="spot_position_lots")
    op.drop_index("ix_spot_position_lots_opened_at", table_name="spot_position_lots")
    op.drop_index("ix_spot_position_lots_execution_intent_id", table_name="spot_position_lots")
    op.drop_index("ix_spot_position_lots_symbol", table_name="spot_position_lots")
    op.drop_table("spot_position_lots")
