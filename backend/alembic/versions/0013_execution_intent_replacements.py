"""execution intent replacements

Revision ID: 0013_intent_replacements
Revises: 0012_spot_position_pnl_fields
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_intent_replacements"
down_revision: str | None = "0012_spot_position_pnl_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution_intents", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("execution_intents", sa.Column("parent_intent_id", sa.BigInteger(), nullable=True))
    op.add_column("execution_intents", sa.Column("replaced_by_intent_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_execution_intents_parent_intent_id", "execution_intents", ["parent_intent_id"])
    op.create_index(
        "ix_execution_intents_replaced_by_intent_id",
        "execution_intents",
        ["replaced_by_intent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_execution_intents_replaced_by_intent_id", table_name="execution_intents")
    op.drop_index("ix_execution_intents_parent_intent_id", table_name="execution_intents")
    op.drop_column("execution_intents", "replaced_by_intent_id")
    op.drop_column("execution_intents", "parent_intent_id")
    op.drop_column("execution_intents", "cancelled_at")
