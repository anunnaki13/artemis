from decimal import Decimal

from services.market_data.bybit import (
    extract_symbol_filters,
    parse_funding_snapshot,
    parse_kline,
    parse_open_interest_snapshot,
    parse_ws_depth_message,
    parse_ws_kline_message,
    parse_ws_ticker_message,
    topic_for_symbol,
)


def test_extract_symbol_filters() -> None:
    payload = {
        "priceFilter": {"tickSize": "0.01000000"},
        "lotSizeFilter": {
            "qtyStep": "0.00010000",
            "minOrderAmt": "5.00000000",
        },
    }
    assert extract_symbol_filters(payload) == {
        "tick_size": Decimal("0.01000000"),
        "step_size": Decimal("0.00010000"),
        "min_notional": Decimal("5.00000000"),
    }


def test_parse_kline() -> None:
    parsed = parse_kline(
        "btcusdt",
        "1m",
        [
            1714492800000,
            "60000.00",
            "60100.00",
            "59900.00",
            "60050.00",
            "12.50",
            "750000.00",
        ],
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["timeframe"] == "1m"
    assert parsed["close"] == Decimal("60050.00")
    assert parsed["quote_volume"] == Decimal("750000.00")


def test_topic_for_symbol() -> None:
    assert topic_for_symbol("btcusdt", "1m") == [
        "kline.1.BTCUSDT",
        "tickers.BTCUSDT",
        "orderbook.50.BTCUSDT",
    ]


def test_parse_ws_kline_message() -> None:
    parsed = parse_ws_kline_message(
        "kline.1.BTCUSDT",
        {
            "data": [
                {
                    "symbol": "BTCUSDT",
                    "start": 1714492800000,
                    "end": 1714492859999,
                    "open": "60000.00",
                    "high": "60100.00",
                    "low": "59900.00",
                    "close": "60050.00",
                    "volume": "12.50",
                    "turnover": "750000.00",
                }
            ]
        },
    )
    assert parsed["source"] == "bybit_ws"
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["quote_volume"] == Decimal("750000.00")


def test_parse_ws_ticker_message() -> None:
    parsed = parse_ws_ticker_message(
        {
            "ts": 1714492860000,
            "data": {
                "symbol": "BTCUSDT",
                "lastPrice": "60055.00",
                "bid1Price": "60054.90",
                "ask1Price": "60055.10",
            },
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["last_price"] == Decimal("60055.00")
    assert parsed["bid_price"] == Decimal("60054.90")
    assert parsed["ask_price"] == Decimal("60055.10")


def test_parse_ws_depth_message() -> None:
    parsed = parse_ws_depth_message(
        "BTCUSDT",
        {
            "ts": 1714492860000,
            "data": {
                "b": [["60054.80", "1.25"]],
                "a": [["60055.20", "0.90"]],
            },
        },
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["bid_price"] == Decimal("60054.80")
    assert parsed["ask_price"] == Decimal("60055.20")


def test_parse_funding_snapshot() -> None:
    parsed = parse_funding_snapshot(
        {
            "symbol": "BTCUSDT",
            "markPrice": "60055.10",
            "fundingRate": "0.00010000",
            "nextFundingTime": 1714492860000,
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["last_price"] == Decimal("60055.10")
    assert parsed["funding_rate"] == Decimal("0.00010000")


def test_parse_open_interest_snapshot() -> None:
    parsed = parse_open_interest_snapshot(
        "BTCUSDT",
        {
            "openInterest": "12345.678",
            "timestamp": 1714492860000,
        },
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["open_interest"] == Decimal("12345.678")
