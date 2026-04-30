from datetime import datetime, timedelta, timezone
from decimal import Decimal

from services.market_data.orderbook import OrderBookMetrics
from services.strategy.orderbook_imbalance import (
    OrderBookImbalanceSnapshot,
    OrderBookImbalanceStrategy,
)


def make_snapshot(
    minutes: int,
    imbalance: Decimal,
    spread_bps: Decimal = Decimal("3"),
    bid_depth: Decimal = Decimal("25000"),
    ask_depth: Decimal = Decimal("24000"),
) -> OrderBookImbalanceSnapshot:
    return OrderBookImbalanceSnapshot(
        symbol="BTCUSDT",
        timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes),
        metrics=OrderBookMetrics(
            spread=Decimal("0.10"),
            spread_bps=spread_bps,
            mid_price=Decimal("100"),
            bid_depth_notional_0p5pct=bid_depth,
            ask_depth_notional_0p5pct=ask_depth,
            imbalance_ratio_0p5pct=imbalance,
            best_bid=Decimal("99.95"),
            best_ask=Decimal("100.05"),
            last_update_id=minutes,
            updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes),
        ),
    )


async def test_orderbook_imbalance_strategy_generates_long_signal() -> None:
    strategy = OrderBookImbalanceStrategy()
    market_data = [
        make_snapshot(0, Decimal("0.16")),
        make_snapshot(1, Decimal("0.18")),
        make_snapshot(2, Decimal("0.22")),
        make_snapshot(3, Decimal("0.24")),
    ]
    params: dict[str, Decimal | int] = {
        "lookback": 4,
        "min_abs_imbalance": Decimal("0.12"),
        "max_spread_bps": Decimal("8"),
        "min_depth_notional_usd": Decimal("10000"),
        "persistence_ratio": Decimal("0.60"),
    }

    signal = await strategy.generate_signal(market_data, params)

    assert signal is not None
    assert signal.side == "long"
    assert signal.source == "orderbook_imbalance"


async def test_orderbook_imbalance_strategy_blocks_wide_spread() -> None:
    strategy = OrderBookImbalanceStrategy()
    market_data = [
        make_snapshot(0, Decimal("-0.14"), spread_bps=Decimal("12")),
        make_snapshot(1, Decimal("-0.15"), spread_bps=Decimal("12")),
        make_snapshot(2, Decimal("-0.18"), spread_bps=Decimal("12")),
    ]
    params: dict[str, Decimal | int] = {
        "lookback": 3,
        "min_abs_imbalance": Decimal("0.12"),
        "max_spread_bps": Decimal("8"),
        "min_depth_notional_usd": Decimal("10000"),
        "persistence_ratio": Decimal("0.60"),
    }

    signal = await strategy.generate_signal(market_data, params)

    assert signal is None
