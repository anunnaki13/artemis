"""spot symbol positions

Revision ID: 0010_spot_symbol_positions
Revises: 0009_spot_account_balances
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_spot_symbol_positions"
down_revision: str | None = "0009_spot_account_balances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_symbol_positions",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("base_asset", sa.String(length=16), nullable=False),
        sa.Column("quote_asset", sa.String(length=16), nullable=False),
        sa.Column("net_quantity", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("average_entry_price", sa.Numeric(28, 12), nullable=True),
        sa.Column("quote_exposure_usd", sa.Numeric(36, 18), nullable=True),
        sa.Column("realized_notional", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source_event", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_spot_symbol_positions_updated_at", "spot_symbol_positions", ["updated_at"])
    op.create_index(
        "ix_spot_symbol_positions_quote_exposure_usd",
        "spot_symbol_positions",
        ["quote_exposure_usd"],
    )


def downgrade() -> None:
    op.drop_index("ix_spot_symbol_positions_quote_exposure_usd", table_name="spot_symbol_positions")
    op.drop_index("ix_spot_symbol_positions_updated_at", table_name="spot_symbol_positions")
    op.drop_table("spot_symbol_positions")
