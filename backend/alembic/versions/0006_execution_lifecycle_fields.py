"""execution lifecycle fields

Revision ID: 0006_execution_lifecycle_fields
Revises: 0005_execution_intents
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_execution_lifecycle_fields"
down_revision: str | None = "0005_execution_intents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_intents", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("execution_intents", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("execution_intents", sa.Column("execution_payload", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("execution_intents", "execution_payload")
    op.drop_column("execution_intents", "executed_at")
    op.drop_column("execution_intents", "dispatched_at")
