"""spot execution fill lot closes

Revision ID: 0018_lot_closes
Revises: 0017_spot_position_lots
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_lot_closes"
down_revision: str | None = "0017_spot_position_lots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_execution_fill_lot_closes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("execution_fill_id", sa.BigInteger(), nullable=False),
        sa.Column("position_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("closed_quantity", sa.Numeric(36, 18), nullable=False),
        sa.Column("lot_entry_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("fill_exit_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("realized_pnl_usd", sa.Numeric(36, 18), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spot_execution_fill_lot_closes_fill_id", "spot_execution_fill_lot_closes", ["execution_fill_id"])
    op.create_index("ix_spot_execution_fill_lot_closes_lot_id", "spot_execution_fill_lot_closes", ["position_lot_id"])
    op.create_index("ix_spot_execution_fill_lot_closes_symbol", "spot_execution_fill_lot_closes", ["symbol"])
    op.create_index("ix_spot_execution_fill_lot_closes_closed_at", "spot_execution_fill_lot_closes", ["closed_at"])


def downgrade() -> None:
    op.drop_index("ix_spot_execution_fill_lot_closes_closed_at", table_name="spot_execution_fill_lot_closes")
    op.drop_index("ix_spot_execution_fill_lot_closes_symbol", table_name="spot_execution_fill_lot_closes")
    op.drop_index("ix_spot_execution_fill_lot_closes_lot_id", table_name="spot_execution_fill_lot_closes")
    op.drop_index("ix_spot_execution_fill_lot_closes_fill_id", table_name="spot_execution_fill_lot_closes")
    op.drop_table("spot_execution_fill_lot_closes")
