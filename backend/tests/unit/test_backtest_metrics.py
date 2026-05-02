from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.market_data import BacktestRun
from app.models.market_data import Candle
from app.routers.backtest import build_group_summary, summarize_buy_and_hold, summarize_range_probe, summarize_strategy_window


def make_candle(index: int, open_: str, high: str, low: str, close: str) -> Candle:
    start = datetime(2026, 5, 1, tzinfo=UTC) + timedelta(minutes=index)
    return Candle(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=start,
        close_time=start + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("10"),
        quote_volume=Decimal("1000"),
        trade_count=10,
        source="bybit",
    )


def test_summarize_buy_and_hold_includes_common_metrics() -> None:
    candles = [
        make_candle(0, "100", "102", "99", "100"),
        make_candle(1, "100", "104", "99", "103"),
        make_candle(2, "103", "106", "101", "105"),
    ]

    summary = summarize_buy_and_hold("BTCUSDT", "1m", "buy_and_hold", candles)

    assert summary["benchmark"] == "buy_and_hold"
    assert Decimal(str(summary["return_pct"])) == Decimal("5")
    assert Decimal(str(summary["max_drawdown_pct"])) >= Decimal("0")
    assert "volatility_pct" in summary
    assert "trend_efficiency_pct" in summary


def test_summarize_range_probe_includes_trade_metrics() -> None:
    candles = [
        make_candle(0, "100", "101", "98", "100"),
        make_candle(1, "100", "100", "95", "96"),
        make_candle(2, "96", "99", "95", "98"),
        make_candle(3, "98", "99", "92", "93"),
        make_candle(4, "93", "97", "92", "95"),
    ]

    summary = summarize_range_probe("BTCUSDT", "1m", "range_probe", candles)

    assert summary["benchmark"] == "range_probe"
    assert summary["trades_count"] == 2
    assert summary["winning_trades"] == 2
    assert Decimal(str(summary["gross_profit_quote"])) > Decimal("0")
    assert Decimal(str(summary["win_rate_pct"])) == Decimal("100")


def test_build_group_summary_aggregates_run_metrics() -> None:
    runs = [
        BacktestRun(
            symbol="BTCUSDT",
            timeframe="1m",
            strategy_name="buy_and_hold",
            sample_size=120,
            status="completed",
            summary_payload={
                "return_pct": "5",
                "average_range_pct": "1.5",
                "max_drawdown_pct": "2",
                "volatility_pct": "0.8",
            },
        ),
        BacktestRun(
            symbol="BTCUSDT",
            timeframe="1m",
            strategy_name="buy_and_hold",
            sample_size=240,
            status="completed",
            summary_payload={
                "return_pct": "-1",
                "average_range_pct": "2.5",
                "max_drawdown_pct": "4",
                "volatility_pct": "1.2",
            },
        ),
    ]

    summary = build_group_summary("buy_and_hold", runs)

    assert summary.group_key == "buy_and_hold"
    assert summary.runs_count == 2
    assert summary.best_return_pct == Decimal("5")
    assert summary.worst_return_pct == Decimal("-1")
    assert summary.average_sample_size == Decimal("180")


def test_summarize_strategy_window_delegates_range_probe() -> None:
    candles = [
        make_candle(0, "100", "101", "98", "100"),
        make_candle(1, "100", "100", "95", "96"),
        make_candle(2, "96", "99", "95", "98"),
        make_candle(3, "98", "99", "92", "93"),
        make_candle(4, "93", "97", "92", "95"),
    ]

    summary = summarize_strategy_window("BTCUSDT", "1m", "range_probe", candles)

    assert summary["strategy_name"] == "range_probe"
    assert summary["trades_count"] == 2
