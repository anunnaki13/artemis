from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=32)
    timeframe: str = Field(default="1m", min_length=1, max_length=8)
    limit: int = Field(default=240, ge=30, le=2000)
    strategy_name: str = Field(default="buy_and_hold", min_length=3, max_length=64)
    notes: str | None = Field(default=None, max_length=512)


class BacktestWalkForwardRequest(BaseModel):
    symbol: str = Field(default="BTCUSDT", min_length=3, max_length=32)
    timeframe: str = Field(default="1m", min_length=1, max_length=8)
    lookback_limit: int = Field(default=720, ge=120, le=4000)
    train_size: int = Field(default=240, ge=30, le=2000)
    test_size: int = Field(default=60, ge=20, le=1000)
    step_size: int = Field(default=60, ge=10, le=1000)
    strategy_name: str = Field(default="buy_and_hold", min_length=3, max_length=64)


class BacktestRunRead(BaseModel):
    id: int
    created_at: datetime
    status: str
    symbol: str
    timeframe: str
    strategy_name: str
    sample_size: int
    summary_payload: dict[str, object]
    notes: str | None


class BacktestSummaryRead(BaseModel):
    symbol: str
    timeframe: str
    strategy_name: str
    sample_size: int
    start_time: datetime
    end_time: datetime
    start_price: Decimal
    end_price: Decimal
    return_pct: Decimal
    high_price: Decimal
    low_price: Decimal
    average_range_pct: Decimal
    realized_pnl_quote: Decimal


class BacktestGroupRead(BaseModel):
    group_key: str
    runs_count: int
    average_return_pct: Decimal
    best_return_pct: Decimal
    worst_return_pct: Decimal
    average_range_pct: Decimal
    average_drawdown_pct: Decimal
    average_volatility_pct: Decimal
    average_sample_size: Decimal


class BacktestOverviewRead(BaseModel):
    symbol: str
    filtered_runs_count: int
    available_strategies: list[str]
    available_timeframes: list[str]
    strategy_groups: list[BacktestGroupRead]
    timeframe_groups: list[BacktestGroupRead]


class BacktestWalkForwardWindowRead(BaseModel):
    window_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    return_pct: Decimal
    max_drawdown_pct: Decimal
    volatility_pct: Decimal
    trades_count: int | None = None
    win_rate_pct: Decimal | None = None


class BacktestWalkForwardRead(BaseModel):
    symbol: str
    timeframe: str
    strategy_name: str
    lookback_limit: int
    train_size: int
    test_size: int
    step_size: int
    windows_count: int
    positive_windows_count: int
    average_return_pct: Decimal
    best_return_pct: Decimal
    worst_return_pct: Decimal
    average_drawdown_pct: Decimal
    average_volatility_pct: Decimal
    average_win_rate_pct: Decimal | None = None
    windows: list[BacktestWalkForwardWindowRead]
