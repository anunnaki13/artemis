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
