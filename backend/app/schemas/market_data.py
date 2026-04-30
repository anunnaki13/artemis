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
