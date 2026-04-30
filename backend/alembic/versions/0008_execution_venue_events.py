"""execution venue events

Revision ID: 0008_execution_venue_events
Revises: 0007_execution_order_ids
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_execution_venue_events"
down_revision: str | None = "0007_execution_order_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_venue_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_intent_id", sa.BigInteger(), nullable=True),
        sa.Column("venue", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("venue_status", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("client_order_id", sa.String(length=128), nullable=True),
        sa.Column("venue_order_id", sa.String(length=128), nullable=True),
        sa.Column("reconcile_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_execution_venue_events_intent_created_at",
        "execution_venue_events",
        ["execution_intent_id", "created_at"],
    )
    op.create_index(
        "ix_execution_venue_events_client_order_id",
        "execution_venue_events",
        ["client_order_id"],
    )
    op.create_index(
        "ix_execution_venue_events_venue_order_id",
        "execution_venue_events",
        ["venue_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_execution_venue_events_venue_order_id", table_name="execution_venue_events")
    op.drop_index("ix_execution_venue_events_client_order_id", table_name="execution_venue_events")
    op.drop_index("ix_execution_venue_events_intent_created_at", table_name="execution_venue_events")
    op.drop_table("execution_venue_events")
