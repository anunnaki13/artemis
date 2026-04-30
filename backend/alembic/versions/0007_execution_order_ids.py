"""execution order ids

Revision ID: 0007_execution_order_ids
Revises: 0006_execution_lifecycle_fields
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_execution_order_ids"
down_revision: str | None = "0006_execution_lifecycle_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_intents", sa.Column("client_order_id", sa.String(length=128), nullable=True))
    op.add_column("execution_intents", sa.Column("venue_order_id", sa.String(length=128), nullable=True))
    op.add_column("execution_intents", sa.Column("execution_venue", sa.String(length=64), nullable=True))
    op.create_index("ix_execution_intents_client_order_id", "execution_intents", ["client_order_id"])
    op.create_index("ix_execution_intents_venue_order_id", "execution_intents", ["venue_order_id"])


def downgrade() -> None:
    op.drop_index("ix_execution_intents_venue_order_id", table_name="execution_intents")
    op.drop_index("ix_execution_intents_client_order_id", table_name="execution_intents")
    op.drop_column("execution_intents", "execution_venue")
    op.drop_column("execution_intents", "venue_order_id")
    op.drop_column("execution_intents", "client_order_id")
