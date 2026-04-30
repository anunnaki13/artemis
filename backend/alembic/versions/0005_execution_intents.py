"""execution intents

Revision ID: 0005_execution_intents
Revises: 0004_orderbook_snapshots
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_execution_intents"
down_revision: str | None = "0004_orderbook_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_intents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("source_strategy", sa.String(length=64), nullable=False),
        sa.Column("requested_notional", sa.Numeric(28, 12), nullable=False),
        sa.Column("approved_notional", sa.Numeric(28, 12), nullable=False),
        sa.Column("entry_price", sa.Numeric(28, 12), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column("signal_payload", postgresql.JSONB(), nullable=False),
        sa.Column("risk_payload", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_execution_intents_symbol", "execution_intents", ["symbol"])
    op.create_index("ix_execution_intents_status", "execution_intents", ["status"])
    op.create_index(
        "ix_execution_intents_status_created_at",
        "execution_intents",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_execution_intents_symbol_created_at",
        "execution_intents",
        ["symbol", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_execution_intents_symbol_created_at", table_name="execution_intents")
    op.drop_index("ix_execution_intents_status_created_at", table_name="execution_intents")
    op.drop_index("ix_execution_intents_status", table_name="execution_intents")
    op.drop_index("ix_execution_intents_symbol", table_name="execution_intents")
    op.drop_table("execution_intents")
