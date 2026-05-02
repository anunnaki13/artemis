"""add backtest runs

Revision ID: 0020_backtest_runs
Revises: 0019_ai_analyst_runs
Create Date: 2026-05-02 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_backtest_runs"
down_revision: str | None = "0019_ai_analyst_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("sample_size", sa.BigInteger(), nullable=False),
        sa.Column("summary_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_runs_created_at", "backtest_runs", ["created_at"], unique=False)
    op.create_index("ix_backtest_runs_symbol_created_at", "backtest_runs", ["symbol", "created_at"], unique=False)
    op.create_index("ix_backtest_runs_status_created_at", "backtest_runs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_status_created_at", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_symbol_created_at", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_created_at", table_name="backtest_runs")
    op.drop_table("backtest_runs")
