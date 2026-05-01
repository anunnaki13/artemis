"""daily digest runs

Revision ID: 0016_daily_digest_runs
Revises: 0015_fill_attr
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_daily_digest_runs"
down_revision: str | None = "0015_fill_attr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_digest_runs",
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fills_count", sa.BigInteger(), nullable=False),
        sa.Column("intents_count", sa.BigInteger(), nullable=False),
        sa.Column("lineage_alerts_count", sa.BigInteger(), nullable=False),
        sa.Column("top_strategy", sa.String(length=64), nullable=True),
        sa.Column("top_strategy_realized_pnl_usd", sa.Numeric(36, 18), nullable=True),
        sa.Column("anomaly_score", sa.BigInteger(), nullable=False),
        sa.Column("anomaly_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("json_path", sa.String(length=512), nullable=False),
        sa.Column("strategy_csv_path", sa.String(length=512), nullable=False),
        sa.Column("lineage_csv_path", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("report_date"),
    )
    op.create_index("ix_daily_digest_runs_generated_at", "daily_digest_runs", ["generated_at"])
    op.create_index("ix_daily_digest_runs_anomaly_score", "daily_digest_runs", ["anomaly_score"])


def downgrade() -> None:
    op.drop_index("ix_daily_digest_runs_anomaly_score", table_name="daily_digest_runs")
    op.drop_index("ix_daily_digest_runs_generated_at", table_name="daily_digest_runs")
    op.drop_table("daily_digest_runs")
