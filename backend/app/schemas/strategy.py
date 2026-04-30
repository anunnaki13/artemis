from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from strategies.base import Signal


class OrderBookImbalanceEvaluateRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=32)
    lookback: int = Field(default=20, ge=3, le=200)
    min_abs_imbalance: Decimal = Field(default=Decimal("0.12"))
    max_spread_bps: Decimal = Field(default=Decimal("8"))
    min_depth_notional_usd: Decimal = Field(default=Decimal("10000"))
    persistence_ratio: Decimal = Field(default=Decimal("0.60"))


class OrderBookImbalanceDiagnosticsResponse(BaseModel):
    sample_size: int
    latest_timestamp: datetime | None
    latest_imbalance_ratio: Decimal | None
    average_imbalance_ratio: Decimal | None
    latest_spread_bps: Decimal | None
    bid_depth_notional_0p5pct: Decimal
    ask_depth_notional_0p5pct: Decimal
    persistence_ratio_observed: Decimal


class StrategyEvaluationResponse(BaseModel):
    strategy: str
    signal: Signal | None
    diagnostics: OrderBookImbalanceDiagnosticsResponse
