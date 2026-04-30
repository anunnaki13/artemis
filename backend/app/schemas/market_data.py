from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SymbolRead(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    market_type: str
    status: str
    min_notional: Decimal | None
    tick_size: Decimal | None
    step_size: Decimal | None
    is_enabled: bool


class SyncSymbolsResponse(BaseModel):
    synced: int
    quote_asset: str | None = None


class CandleIngestRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=32)
    interval: str = Field(default="1m", min_length=1, max_length=8)
    limit: int = Field(default=500, ge=1, le=1000)


class CandleIngestResponse(BaseModel):
    symbol: str
    interval: str
    ingested: int


class MarketStreamStartRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT"], min_length=1, max_length=25)
    interval: str = Field(default="1m", min_length=1, max_length=8)


class MarketStreamStatusResponse(BaseModel):
    running: bool
    symbols: list[str]
    interval: str | None
    reconnect_attempts: int
    messages_processed: int
    poll_cycles: int
    last_message_at: datetime | None
    last_error: str | None


class OrderBookLevel(BaseModel):
    price: Decimal
    quantity: Decimal


class OrderBookMetricsResponse(BaseModel):
    spread: Decimal | None
    spread_bps: Decimal | None
    mid_price: Decimal | None
    bid_depth_notional_0p5pct: Decimal
    ask_depth_notional_0p5pct: Decimal
    imbalance_ratio_0p5pct: Decimal | None
    best_bid: Decimal | None
    best_ask: Decimal | None
    last_update_id: int | None
    updated_at: datetime | None


class OrderBookStateResponse(BaseModel):
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    metrics: OrderBookMetricsResponse


class LiquidityMetricsPointResponse(BaseModel):
    symbol: str
    timestamp: datetime
    metrics: OrderBookMetricsResponse


class OrderBookSnapshotPointResponse(BaseModel):
    symbol: str
    timestamp: datetime
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    metrics: OrderBookMetricsResponse


class CandleRead(BaseModel):
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
