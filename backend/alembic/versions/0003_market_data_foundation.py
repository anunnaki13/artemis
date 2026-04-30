"""market data foundation

Revision ID: 0003_market_data_foundation
Revises: 0002_app_settings
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_market_data_foundation"
down_revision: str | None = "0002_app_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("symbol", sa.String(length=32), primary_key=True),
        sa.Column("base_asset", sa.String(length=16), nullable=False),
        sa.Column("quote_asset", sa.String(length=16), nullable=False),
        sa.Column("market_type", sa.String(length=16), nullable=False, server_default="spot"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="TRADING"),
        sa.Column("min_notional", sa.Numeric(28, 12), nullable=True),
        sa.Column("tick_size", sa.Numeric(28, 12), nullable=True),
        sa.Column("step_size", sa.Numeric(28, 12), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "candles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(28, 12), nullable=False),
        sa.Column("high", sa.Numeric(28, 12), nullable=False),
        sa.Column("low", sa.Numeric(28, 12), nullable=False),
        sa.Column("close", sa.Numeric(28, 12), nullable=False),
        sa.Column("volume", sa.Numeric(36, 12), nullable=False),
        sa.Column("quote_volume", sa.Numeric(36, 12), nullable=True),
        sa.Column("trade_count", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="binance"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("symbol", "timeframe", "open_time", name="uq_candles_symbol_timeframe_open_time"),
    )
    op.create_index("ix_candles_symbol", "candles", ["symbol"])
    op.create_index("ix_candles_timeframe", "candles", ["timeframe"])
    op.create_index("ix_candles_open_time", "candles", ["open_time"])
    op.create_index("ix_candles_symbol_timeframe_open_time", "candles", ["symbol", "timeframe", "open_time"])
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid_price", sa.Numeric(28, 12), nullable=True),
        sa.Column("ask_price", sa.Numeric(28, 12), nullable=True),
        sa.Column("last_price", sa.Numeric(28, 12), nullable=True),
        sa.Column("funding_rate", sa.Numeric(18, 12), nullable=True),
        sa.Column("open_interest", sa.Numeric(36, 12), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_market_snapshots_symbol", "market_snapshots", ["symbol"])
    op.create_index("ix_market_snapshots_timestamp", "market_snapshots", ["timestamp"])
    op.create_index("ix_market_snapshots_symbol_timestamp", "market_snapshots", ["symbol", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_market_snapshots_symbol_timestamp", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_timestamp", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_symbol", table_name="market_snapshots")
    op.drop_table("market_snapshots")
    op.drop_index("ix_candles_symbol_timeframe_open_time", table_name="candles")
    op.drop_index("ix_candles_open_time", table_name="candles")
    op.drop_index("ix_candles_timeframe", table_name="candles")
    op.drop_index("ix_candles_symbol", table_name="candles")
    op.drop_table("candles")
    op.drop_table("symbols")
