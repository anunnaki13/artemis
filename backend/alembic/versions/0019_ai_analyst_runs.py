"""add ai analyst runs

Revision ID: 0019_ai_analyst_runs
Revises: 0018_lot_closes
Create Date: 2026-05-02 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0019_ai_analyst_runs"
down_revision: str | None = "0018_lot_closes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_analyst_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("output_tokens", sa.BigInteger(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("budget_limit_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("budget_spent_before_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("context_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyst_runs_created_at", "ai_analyst_runs", ["created_at"], unique=False)
    op.create_index("ix_ai_analyst_runs_mode_created_at", "ai_analyst_runs", ["mode", "created_at"], unique=False)
    op.create_index("ix_ai_analyst_runs_status_created_at", "ai_analyst_runs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_analyst_runs_status_created_at", table_name="ai_analyst_runs")
    op.drop_index("ix_ai_analyst_runs_mode_created_at", table_name="ai_analyst_runs")
    op.drop_index("ix_ai_analyst_runs_created_at", table_name="ai_analyst_runs")
    op.drop_table("ai_analyst_runs")
