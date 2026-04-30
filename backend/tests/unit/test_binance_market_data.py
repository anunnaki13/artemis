from decimal import Decimal

from services.market_data.binance import (
    build_combined_stream_url,
    extract_symbol_filters,
    parse_kline,
    parse_funding_snapshot,
    parse_open_interest_snapshot,
    parse_ws_book_ticker_message,
    parse_ws_depth_message,
    parse_ws_kline_message,
    parse_ws_mini_ticker_message,
)


def test_extract_symbol_filters() -> None:
    payload = {
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
            {"filterType": "LOT_SIZE", "stepSize": "0.00010000"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "5.00000000"},
        ]
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
            1714492859999,
            "750000.00",
            1234,
        ],
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["timeframe"] == "1m"
    assert parsed["close"] == Decimal("60050.00")
    assert parsed["trade_count"] == 1234


def test_build_combined_stream_url() -> None:
    url = build_combined_stream_url("wss://stream.binance.com:9443", ["ethusdt", "BTCUSDT"], "1m")
    assert (
        url
        == "wss://stream.binance.com:9443/stream?"
        "streams=btcusdt@kline_1m/btcusdt@miniTicker/btcusdt@bookTicker/btcusdt@depth@100ms/"
        "ethusdt@kline_1m/ethusdt@miniTicker/ethusdt@bookTicker/ethusdt@depth@100ms"
    )


def test_parse_ws_kline_message() -> None:
    parsed = parse_ws_kline_message(
        {
            "e": "kline",
            "s": "BTCUSDT",
            "k": {
                "t": 1714492800000,
                "T": 1714492859999,
                "i": "1m",
                "o": "60000.00",
                "h": "60100.00",
                "l": "59900.00",
                "c": "60050.00",
                "v": "12.50",
                "q": "750000.00",
                "n": 1234,
            },
        }
    )
    assert parsed["source"] == "binance_ws"
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["quote_volume"] == Decimal("750000.00")


def test_parse_ws_mini_ticker_message() -> None:
    parsed = parse_ws_mini_ticker_message(
        {
            "e": "24hrMiniTicker",
            "E": 1714492860000,
            "s": "BTCUSDT",
            "c": "60055.00",
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["last_price"] == Decimal("60055.00")


def test_parse_ws_book_ticker_message() -> None:
    parsed = parse_ws_book_ticker_message(
        {
            "E": 1714492860000,
            "s": "BTCUSDT",
            "b": "60054.90",
            "a": "60055.10",
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["bid_price"] == Decimal("60054.90")
    assert parsed["ask_price"] == Decimal("60055.10")


def test_parse_ws_depth_message() -> None:
    parsed = parse_ws_depth_message(
        {
            "e": "depthUpdate",
            "E": 1714492860000,
            "s": "BTCUSDT",
            "b": [["60054.80", "1.25"]],
            "a": [["60055.20", "0.90"]],
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["bid_price"] == Decimal("60054.80")
    assert parsed["ask_price"] == Decimal("60055.20")


def test_parse_funding_snapshot() -> None:
    parsed = parse_funding_snapshot(
        {
            "symbol": "BTCUSDT",
            "markPrice": "60055.10",
            "lastFundingRate": "0.00010000",
            "time": 1714492860000,
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["last_price"] == Decimal("60055.10")
    assert parsed["funding_rate"] == Decimal("0.00010000")


def test_parse_open_interest_snapshot() -> None:
    parsed = parse_open_interest_snapshot(
        {
            "symbol": "BTCUSDT",
            "openInterest": "12345.678",
            "time": 1714492860000,
        }
    )
    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["open_interest"] == Decimal("12345.678")
