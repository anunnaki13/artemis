"""spot account balances

Revision ID: 0009_spot_account_balances
Revises: 0008_execution_venue_events
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_spot_account_balances"
down_revision: str | None = "0008_execution_venue_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spot_account_balances",
        sa.Column("asset", sa.String(length=32), primary_key=True),
        sa.Column("free", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("locked", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(36, 18), nullable=False, server_default="0"),
        sa.Column("total_value_usd", sa.Numeric(36, 18), nullable=True),
        sa.Column("last_delta", sa.Numeric(36, 18), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source_event", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_spot_account_balances_total_value_usd",
        "spot_account_balances",
        ["total_value_usd"],
    )
    op.create_index(
        "ix_spot_account_balances_updated_at",
        "spot_account_balances",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_spot_account_balances_updated_at", table_name="spot_account_balances")
    op.drop_index("ix_spot_account_balances_total_value_usd", table_name="spot_account_balances")
    op.drop_table("spot_account_balances")
