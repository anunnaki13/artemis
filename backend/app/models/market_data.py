from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Symbol(Base):
    __tablename__ = "symbols"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_asset: Mapped[str] = mapped_column(String(16))
    quote_asset: Mapped[str] = mapped_column(String(16))
    market_type: Mapped[str] = mapped_column(String(16), default="spot")
    status: Mapped[str] = mapped_column(String(32), default="TRADING")
    min_notional: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    tick_size: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    step_size: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "open_time", name="uq_candles_symbol_timeframe_open_time"),
        Index("ix_candles_symbol_timeframe_open_time", "symbol", "timeframe", "open_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    high: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    low: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    close: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    volume: Mapped[Decimal] = mapped_column(Numeric(36, 12))
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(36, 12), nullable=True)
    trade_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="bybit")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (Index("ix_market_snapshots_symbol_timestamp", "symbol", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    bid_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    ask_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    funding_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 12), nullable=True)
    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(36, 12), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class OrderBookSnapshot(Base):
    __tablename__ = "orderbook_snapshots"
    __table_args__ = (Index("ix_orderbook_snapshots_symbol_timestamp", "symbol", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_update_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bids: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    asks: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ExecutionIntent(Base):
    __tablename__ = "execution_intents"
    __table_args__ = (
        Index("ix_execution_intents_status_created_at", "status", "created_at"),
        Index("ix_execution_intents_symbol_created_at", "symbol", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued")
    source_strategy: Mapped[str] = mapped_column(String(64))
    requested_notional: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    approved_notional: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    venue_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    execution_venue: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_intent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    replaced_by_intent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(64))
    signal_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    risk_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    execution_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)


class ExecutionVenueEvent(Base):
    __tablename__ = "execution_venue_events"
    __table_args__ = (
        Index("ix_execution_venue_events_intent_created_at", "execution_intent_id", "created_at"),
        Index("ix_execution_venue_events_client_order_id", "client_order_id"),
        Index("ix_execution_venue_events_venue_order_id", "venue_order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_intent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    venue: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(64))
    venue_status: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    venue_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reconcile_state: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class SpotAccountBalance(Base):
    __tablename__ = "spot_account_balances"
    __table_args__ = (
        Index("ix_spot_account_balances_total_value_usd", "total_value_usd"),
        Index("ix_spot_account_balances_updated_at", "updated_at"),
    )

    asset: Mapped[str] = mapped_column(String(32), primary_key=True)
    free: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    locked: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    total_value_usd: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    last_delta: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    source_event: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpotSymbolPosition(Base):
    __tablename__ = "spot_symbol_positions"
    __table_args__ = (
        Index("ix_spot_symbol_positions_updated_at", "updated_at"),
        Index("ix_spot_symbol_positions_quote_exposure_usd", "quote_exposure_usd"),
    )

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_asset: Mapped[str] = mapped_column(String(16))
    quote_asset: Mapped[str] = mapped_column(String(16))
    net_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    last_mark_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    quote_exposure_usd: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    market_value_usd: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    realized_notional: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    realized_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    unrealized_pnl_usd: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    source_event: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpotOrderFillState(Base):
    __tablename__ = "spot_order_fill_states"
    __table_args__ = (
        Index("ix_spot_order_fill_states_updated_at", "updated_at"),
        Index("ix_spot_order_fill_states_client_order_id", "client_order_id"),
        Index("ix_spot_order_fill_states_venue_order_id", "venue_order_id"),
    )

    order_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(16))
    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    venue_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cumulative_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    cumulative_quote_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    last_trade_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    source_event: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpotExecutionFill(Base):
    __tablename__ = "spot_execution_fills"
    __table_args__ = (
        Index("ix_spot_execution_fills_symbol_filled_at", "symbol", "filled_at"),
        Index("ix_spot_execution_fills_client_order_id", "client_order_id"),
        Index("ix_spot_execution_fills_venue_order_id", "venue_order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    execution_intent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    source_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    venue_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trade_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    quote_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    realized_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    post_fill_net_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    post_fill_average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    source_event: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpotPositionLot(Base):
    __tablename__ = "spot_position_lots"
    __table_args__ = (
        Index("ix_spot_position_lots_symbol_opened_at", "symbol", "opened_at"),
        Index("ix_spot_position_lots_remaining_quantity", "remaining_quantity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    execution_intent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    source_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    venue_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    source_event: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SpotExecutionFillLotClose(Base):
    __tablename__ = "spot_execution_fill_lot_closes"
    __table_args__ = (
        Index("ix_spot_execution_fill_lot_closes_fill_id", "execution_fill_id"),
        Index("ix_spot_execution_fill_lot_closes_lot_id", "position_lot_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    execution_fill_id: Mapped[int] = mapped_column(BigInteger, index=True)
    position_lot_id: Mapped[int] = mapped_column(BigInteger, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    closed_quantity: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    lot_entry_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    fill_exit_price: Mapped[Decimal] = mapped_column(Numeric(28, 12))
    realized_pnl_usd: Mapped[Decimal] = mapped_column(Numeric(36, 18), default=Decimal("0"))
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class DailyDigestRun(Base):
    __tablename__ = "daily_digest_runs"
    __table_args__ = (
        Index("ix_daily_digest_runs_generated_at", "generated_at"),
        Index("ix_daily_digest_runs_anomaly_score", "anomaly_score"),
    )

    report_date: Mapped[date] = mapped_column(Date(), primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    fills_count: Mapped[int] = mapped_column(BigInteger, default=0)
    intents_count: Mapped[int] = mapped_column(BigInteger, default=0)
    lineage_alerts_count: Mapped[int] = mapped_column(BigInteger, default=0)
    top_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    top_strategy_realized_pnl_usd: Mapped[Decimal | None] = mapped_column(Numeric(36, 18), nullable=True)
    anomaly_score: Mapped[int] = mapped_column(BigInteger, default=0)
    anomaly_flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    json_path: Mapped[str] = mapped_column(String(512))
    strategy_csv_path: Mapped[str] = mapped_column(String(512))
    lineage_csv_path: Mapped[str] = mapped_column(String(512))
