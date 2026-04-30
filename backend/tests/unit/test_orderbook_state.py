from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import pytest

from services.market_data.orderbook import OrderBookState
from services.market_data.orderbook import (
    levels_from_payload,
    levels_to_payload,
    metrics_from_payload,
    metrics_to_payload,
)


def test_orderbook_snapshot_and_metrics() -> None:
    orderbook = OrderBookState(symbol="BTCUSDT")
    orderbook.load_snapshot(
        bids=[["100.0", "2.0"], ["99.7", "1.5"], ["99.4", "1.0"]],
        asks=[["100.2", "1.0"], ["100.4", "1.3"], ["100.6", "1.7"]],
        last_update_id=10,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    metrics = orderbook.metrics()

    assert metrics.best_bid == Decimal("100.0")
    assert metrics.best_ask == Decimal("100.2")
    assert metrics.spread == Decimal("0.2")
    assert metrics.mid_price == Decimal("100.1")
    assert metrics.bid_depth_notional_0p5pct == Decimal("349.55")
    assert metrics.ask_depth_notional_0p5pct == Decimal("401.74")
    assert metrics.imbalance_ratio_0p5pct is not None
    assert metrics.imbalance_ratio_0p5pct.quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    ) == Decimal("-0.069467")


def test_orderbook_applies_depth_update() -> None:
    orderbook = OrderBookState(symbol="BTCUSDT")
    orderbook.load_snapshot(
        bids=[["100.0", "2.0"], ["99.7", "1.5"]],
        asks=[["100.2", "1.0"], ["100.4", "1.3"]],
        last_update_id=10,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    applied = orderbook.apply_depth_update(
        first_update_id=11,
        final_update_id=12,
        bids=[["100.0", "2.5"], ["99.7", "0"]],
        asks=[["100.2", "0.8"], ["100.5", "1.1"]],
        updated_at=datetime(2026, 5, 1, 0, 1, tzinfo=timezone.utc),
    )

    assert applied is True
    assert orderbook.last_update_id == 12
    assert [level.price for level in orderbook.top_bids(5)] == [Decimal("100.0")]
    assert [level.price for level in orderbook.top_asks(5)] == [
        Decimal("100.2"),
        Decimal("100.4"),
        Decimal("100.5"),
    ]


def test_orderbook_rejects_update_gap() -> None:
    orderbook = OrderBookState(symbol="BTCUSDT")
    orderbook.load_snapshot(
        bids=[["100.0", "2.0"]],
        asks=[["100.2", "1.0"]],
        last_update_id=10,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="gap detected"):
        orderbook.apply_depth_update(
            first_update_id=15,
            final_update_id=16,
            bids=[],
            asks=[],
            updated_at=datetime(2026, 5, 1, 0, 1, tzinfo=timezone.utc),
        )


def test_metrics_payload_round_trip() -> None:
    orderbook = OrderBookState(symbol="BTCUSDT")
    orderbook.load_snapshot(
        bids=[["100.0", "2.0"], ["99.7", "1.5"]],
        asks=[["100.2", "1.0"], ["100.4", "1.3"]],
        last_update_id=10,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    metrics = orderbook.metrics()
    payload = {"metrics": metrics_to_payload(metrics)}
    parsed_metrics = metrics_from_payload(payload, datetime(2026, 5, 1, tzinfo=timezone.utc))

    assert parsed_metrics is not None
    assert parsed_metrics.spread == metrics.spread
    assert parsed_metrics.bid_depth_notional_0p5pct == metrics.bid_depth_notional_0p5pct
    assert parsed_metrics.ask_depth_notional_0p5pct == metrics.ask_depth_notional_0p5pct
    assert parsed_metrics.last_update_id == metrics.last_update_id


def test_levels_payload_round_trip() -> None:
    orderbook = OrderBookState(symbol="BTCUSDT")
    orderbook.load_snapshot(
        bids=[["100.0", "2.0"], ["99.7", "1.5"]],
        asks=[["100.2", "1.0"], ["100.4", "1.3"]],
        last_update_id=10,
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    payload = levels_to_payload(orderbook.top_bids(2))
    levels = levels_from_payload(payload)

    assert len(levels) == 2
    assert levels[0].price == Decimal("100.0")
    assert levels[0].quantity == Decimal("2.0")
