from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Numeric, String, UniqueConstraint, func
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
    source: Mapped[str] = mapped_column(String(32), default="binance")
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
