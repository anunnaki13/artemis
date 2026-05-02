"""add ai review fields and recovery events

Revision ID: 0021_ai_review_recovery
Revises: 0020_backtest_runs
Create Date: 2026-05-02 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_ai_review_recovery"
down_revision: str | None = "0020_backtest_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_analyst_runs",
        sa.Column("review_status", sa.String(length=32), server_default="pending", nullable=False),
    )
    op.add_column("ai_analyst_runs", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_analyst_runs", sa.Column("reviewed_by_user_id", sa.String(length=64), nullable=True))
    op.add_column("ai_analyst_runs", sa.Column("review_notes", sa.String(length=512), nullable=True))
    op.create_table(
        "recovery_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("heartbeat_ping_ok", sa.Boolean(), nullable=True),
        sa.Column("dead_man_delivered", sa.Boolean(), nullable=True),
        sa.Column("telegram_delivered", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_events_created_at", "recovery_events", ["created_at"], unique=False)
    op.create_index("ix_recovery_events_status_created_at", "recovery_events", ["status", "created_at"], unique=False)
    op.create_index("ix_recovery_events_severity_created_at", "recovery_events", ["severity", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_recovery_events_severity_created_at", table_name="recovery_events")
    op.drop_index("ix_recovery_events_status_created_at", table_name="recovery_events")
    op.drop_index("ix_recovery_events_created_at", table_name="recovery_events")
    op.drop_table("recovery_events")
    op.drop_column("ai_analyst_runs", "review_notes")
    op.drop_column("ai_analyst_runs", "reviewed_by_user_id")
    op.drop_column("ai_analyst_runs", "reviewed_at")
    op.drop_column("ai_analyst_runs", "review_status")
