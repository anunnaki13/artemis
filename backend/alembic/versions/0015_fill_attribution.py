"""fill attribution

Revision ID: 0015_fill_attr
Revises: 0014_spot_exec_fills
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_fill_attr"
down_revision: str | None = "0014_spot_exec_fills"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("spot_execution_fills", sa.Column("execution_intent_id", sa.BigInteger(), nullable=True))
    op.add_column("spot_execution_fills", sa.Column("source_strategy", sa.String(length=64), nullable=True))
    op.create_index("ix_spot_execution_fills_execution_intent_id", "spot_execution_fills", ["execution_intent_id"])


def downgrade() -> None:
    op.drop_index("ix_spot_execution_fills_execution_intent_id", table_name="spot_execution_fills")
    op.drop_column("spot_execution_fills", "source_strategy")
    op.drop_column("spot_execution_fills", "execution_intent_id")
